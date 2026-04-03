"""
IPO Result Checker using requests library and MeroShare API endpoints.
This script checks IPO application results for all users and updates the database.
"""
import asyncio
import requests
from time import perf_counter
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from database.database import get_db
from database.models import Result, User, UserResult
from utils.helpers import get_dir_path, get_fernet_key, get_logger

# API Base URL
BASE_URL = "https://webbackend.cdsc.com.np"

# Headers template
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Origin": "https://meroshare.cdsc.com.np",
    "Referer": "https://meroshare.cdsc.com.np/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Connection": "keep-alive",
}

log = None
db_lock = None


def get_client_id(dp_code: str) -> Optional[int]:
    """
    Get client ID from DP code.

    Args:
        dp_code: DP code (e.g., "12300")

    Returns:
        Client ID if found, None otherwise
    """
    try:
        url = f"{BASE_URL}/api/meroShare/capital/"
        headers = HEADERS.copy()
        headers["Authorization"] = "null"

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        capitals = response.json()
        for capital in capitals:
            if capital.get("code") == dp_code:
                log.debug(f"Found client ID {capital['id']} for DP {dp_code} ({capital['name']})")
                return capital["id"]

        log.error(f"DP code {dp_code} not found in capital list")
        return None

    except Exception as e:
        log.error(f"Error getting client ID for DP {dp_code}: {e}")
        return None


def login(client_id: int, username: str, password: str) -> Optional[str]:
    """
    Login to MeroShare and get authorization token.

    Args:
        client_id: Client ID from DP
        username: MeroShare username (BOID)
        password: MeroShare password

    Returns:
        Authorization token if successful, None otherwise
    """
    try:
        url = f"{BASE_URL}/api/meroShare/auth/"
        headers = HEADERS.copy()
        headers["Authorization"] = "null"
        headers["Content-Type"] = "application/json"

        payload = {
            "clientId": client_id,
            "username": username,
            "password": password
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        # Token is in response headers
        auth_token = response.headers.get("Authorization")
        if auth_token:
            log.debug(f"Successfully logged in for user {username}")
            return auth_token
        else:
            log.error(f"No authorization token in response for user {username}")
            return None

    except Exception as e:
        log.error(f"Error logging in for user {username}: {e}")
        return None


def get_applications(auth_token: str) -> Optional[List[Dict]]:
    """
    Get all IPO applications for the logged-in user.

    Args:
        auth_token: Authorization token from login

    Returns:
        List of application dictionaries if successful, None otherwise
    """
    try:
        url = f"{BASE_URL}/api/meroShare/applicantForm/active/search/"
        headers = HEADERS.copy()
        headers["Authorization"] = auth_token
        headers["Content-Type"] = "application/json"

        payload = {
            "filterFieldParams": [
                {
                    "key": "companyShare.companyIssue.companyISIN.script",
                    "alias": "Scrip"
                },
                {
                    "key": "companyShare.companyIssue.companyISIN.company.name",
                    "alias": "Company Name"
                }
            ],
            "page": 1,
            "size": 200,
            "searchRoleViewConstants": "VIEW_APPLICANT_FORM_COMPLETE",
            "filterDateParams": [
                {"key": "appliedDate", "condition": "", "alias": "", "value": ""},
                {"key": "appliedDate", "condition": "", "alias": "", "value": ""}
            ]
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        applications = data.get("object", [])
        log.debug(f"Found {len(applications)} applications")

        return applications

    except Exception as e:
        log.error(f"Error getting applications: {e}")
        return None


def get_application_details(auth_token: str, applicant_form_id: int) -> Optional[Dict]:
    """
    Get detailed information about a specific application.

    Args:
        auth_token: Authorization token from login
        applicant_form_id: Application form ID

    Returns:
        Application details dictionary if successful, None otherwise
    """
    try:
        url = f"{BASE_URL}/api/meroShare/applicantForm/report/detail/{applicant_form_id}"
        headers = HEADERS.copy()
        headers["Authorization"] = auth_token

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        details = response.json()
        log.debug(f"Got details for application {applicant_form_id}")

        return details

    except Exception as e:
        log.error(f"Error getting application details for {applicant_form_id}: {e}")
        return None


async def process_user(user_data: List, session: requests.Session) -> Dict:
    """
    Process IPO results for a single user.

    Args:
        user_data: List containing [name, dp, boid, password, crn, pin, account, id]
        session: Requests session

    Returns:
        Dictionary with success status and details
    """
    name, dp, boid, password, crn, pin, account, user_id = user_data

    log.info(f"Processing user: {name}")

    try:
        # Get client ID from DP
        client_id = get_client_id(dp)
        if not client_id:
            return {
                "success": False,
                "error": f"Failed to get client ID for DP {dp}",
                "companies_checked": 0
            }

        # Login
        auth_token = login(client_id, boid, password)
        if not auth_token:
            return {
                "success": False,
                "error": "Failed to login",
                "companies_checked": 0
            }

        # Get applications
        applications = get_applications(auth_token)
        if applications is None:
            return {
                "success": False,
                "error": "Failed to get applications",
                "companies_checked": 0
            }

        if not applications:
            log.info(f"No applications found for user {name}")
            return {
                "success": True,
                "companies_checked": 0
            }

        # Process each application
        async with db_lock:
            with get_db() as db:
                for app in applications:
                    company_share_id = app.get("companyShareId")
                    scrip = app.get("scrip")
                    company_name = app.get("companyName")
                    share_type_name = app.get("shareTypeName")
                    applicant_form_id = app.get("applicantFormId")

                    if not all([company_share_id, scrip, company_name, share_type_name, applicant_form_id]):
                        log.warning(f"Incomplete application data for {name}: {app}")
                        continue

                    # Get or create Result entry
                    result = db.query(Result).filter(
                        Result.company_share_id == company_share_id
                    ).first()

                    if not result:
                        result = Result(
                            company_share_id=company_share_id,
                            script=scrip,
                            share_type_name=share_type_name,
                            company_name=company_name
                        )
                        db.add(result)
                        db.commit()
                        db.refresh(result)
                        log.debug(f"Created new result entry for {scrip} ({company_name})")

                    # Get application details
                    details = get_application_details(auth_token, applicant_form_id)
                    if not details:
                        log.warning(f"Failed to get details for application {applicant_form_id}")
                        continue

                    # Extract details
                    applied_date = details.get("appliedDate")
                    amount = str(details.get("amount", ""))
                    reason_or_remark = details.get("reasonOrRemark")
                    meroshare_remark = details.get("meroshareRemark")
                    received_kitta = details.get("receivedKitta", 0)
                    status_name = details.get("statusName", "")

                    # Create or update UserResult
                    user_result = db.query(UserResult).filter(
                        UserResult.applicant_form_id == applicant_form_id
                    ).first()

                    # Legacy fields for compatibility
                    result_type = share_type_name
                    value = f"{status_name} - {reason_or_remark or ''}"

                    if user_result:
                        # Update existing record
                        user_result.applied_date = applied_date
                        user_result.amount = amount
                        user_result.reason_or_remark = reason_or_remark
                        user_result.meroshare_remark = meroshare_remark
                        user_result.received_kitta = received_kitta
                        user_result.value = value
                        log.debug(f"Updated result for {name} - {scrip}")
                    else:
                        # Create new record
                        user_result = UserResult(
                            user_id=user_id,
                            result_id=result.id,
                            applicant_form_id=applicant_form_id,
                            applied_date=applied_date,
                            amount=amount,
                            reason_or_remark=reason_or_remark,
                            meroshare_remark=meroshare_remark,
                            received_kitta=received_kitta,
                            type=result_type,
                            value=value
                        )
                        db.add(user_result)
                        log.debug(f"Created new result for {name} - {scrip}")

                    db.commit()

                log.info(f"Successfully processed {len(applications)} applications for {name}")

        return {
            "success": True,
            "companies_checked": len(applications)
        }

    except Exception as e:
        log.error(f"Error processing user {name}: {e}")
        import traceback
        log.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "companies_checked": 0
        }


async def ipo_result_async(user_delay: int = 5):
    """
    Main async function to check IPO results for all users.

    Args:
        user_delay: Delay in seconds between starting each user

    Returns:
        Summary of results
    """
    global log, db_lock

    log = get_logger("ipo-result-requests")
    db_lock = asyncio.Lock()

    log.info("=" * 60)
    log.info("Starting IPO Result Checker (Requests)")
    log.info(f"User Start Delay: {user_delay} seconds")
    log.info("=" * 60)

    # Get encryption key
    fernet = get_fernet_key()
    if not fernet:
        log.error("Encryption key not found - cannot decrypt user credentials")
        return

    # Load all users from database
    try:
        with get_db() as db:
            users = db.query(User).all()
            if not users:
                log.warning("No users found in database")
                return

            user_data = []
            for user in users:
                try:
                    decrypted_password = fernet.decrypt(user.passsword.encode()).decode()
                    decrypted_pin = fernet.decrypt(user.pin.encode()).decode()
                    user_data.append([
                        user.name,
                        user.dp,
                        user.boid,
                        decrypted_password,
                        user.crn,
                        decrypted_pin,
                        user.account,
                        user.id
                    ])
                except Exception as e:
                    log.error(f"Error decrypting credentials for user {user.name}: {e}")
                    continue

            log.info(f"Loaded {len(user_data)} users from database")

    except Exception as e:
        log.error(f"Error loading users from database: {e}")
        return

    if not user_data:
        log.warning("No valid users to process")
        return

    start_time = perf_counter()

    # Create a shared session for all requests
    session = requests.Session()

    # Process users with staggered start
    tasks = []
    log.info(f"Creating tasks for {len(user_data)} users with {user_delay}s delay between each")

    for i, user in enumerate(user_data):
        if i > 0:
            log.debug(f"Waiting {user_delay}s before starting user {user[0]}")
            await asyncio.sleep(user_delay)

        task = asyncio.create_task(process_user(user, session))
        tasks.append((task, user[0], user[7]))  # task, username, user_id
        log.info(f"Started task {i + 1}/{len(user_data)} for user: {user[0]}")

    # Wait for all tasks to complete
    log.info("All tasks started. Waiting for completion...")

    completed_users = []
    failed_users = []
    results_summary = []

    for task, username, user_id in tasks:
        try:
            result = await asyncio.wait_for(task, timeout=180)  # 3 minute timeout per user

            if result["success"]:
                completed_users.append(username)
                log.info(f"Successfully completed for user: {username} ({result['companies_checked']} companies)")
                results_summary.append({
                    "user": username,
                    "status": "success",
                    "companies": result["companies_checked"]
                })
            else:
                failed_users.append(username)
                error_msg = result.get("error", "Unknown error")
                log.warning(f"Failed for user: {username} - {error_msg}")
                results_summary.append({
                    "user": username,
                    "status": "failed",
                    "error": error_msg
                })

        except Exception as e:
            failed_users.append(username)
            log.error(f"Exception for user {username}: {e}")
            results_summary.append({
                "user": username,
                "status": "exception",
                "error": str(e)
            })

    # Close session
    session.close()

    end_time = perf_counter()
    time_delta = end_time - start_time
    minutes, seconds = divmod(time_delta, 60)

    # Print summary
    log.info("=" * 60)
    log.info("IPO Result Check Summary")
    log.info("=" * 60)
    log.info(f"Total Users: {len(user_data)}")
    log.info(f"Successful: {len(completed_users)}")
    log.info(f"Failed: {len(failed_users)}")
    log.info(f"Total Time: {int(minutes)} minutes {seconds:.1f} seconds")
    log.info("=" * 60)

    if completed_users:
        log.info(f"Successful users: {', '.join(completed_users)}")

    if failed_users:
        log.warning(f"Failed users: {', '.join(failed_users)}")

    # Detailed summary
    log.debug("Detailed Results:")
    for summary in results_summary:
        if summary["status"] == "success":
            log.debug(f"  {summary['user']}: {summary['companies']} companies checked")
        else:
            log.debug(f"  {summary['user']}: {summary.get('error', 'Failed')}")

    log.info("IPO Result Check Completed")
    return {
        "total": len(user_data),
        "successful": len(completed_users),
        "failed": len(failed_users),
        "time_seconds": time_delta,
        "results": results_summary
    }


def ipo_result(user_delay: int = 5):
    """
    Synchronous wrapper for ipo_result_async.

    Args:
        user_delay: Delay in seconds between starting each user (default: 5)

    Returns:
        Summary of results
    """
    return asyncio.run(ipo_result_async(user_delay=user_delay))


if __name__ == "__main__":
    ipo_result()
