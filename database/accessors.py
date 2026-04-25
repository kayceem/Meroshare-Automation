from contextlib import contextmanager

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Application, Result, User, UserResult
from database.schemas import (
    ApplicationCreate,
    ApplicationFeedItem,
    ApplicationRead,
    CompanyStats,
    CompanyUserResult,
    ResultCreate,
    ResultFeedItem,
    ResultRead,
    UserCompanyResult,
    UserApplicationItem,
    UserRead,
    UserResultCreate,
    UserResultRead,
    UserResultUpdate,
    UserStats,
    UserUpsert,
)


class UserAccessor:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self, apply_ipo: bool | None = None) -> list[UserRead]:
        query = self.session.query(User)
        if apply_ipo is not None:
            query = query.filter(User.apply_ipo == apply_ipo)
        users = query.all()
        return [UserRead.model_validate(user) for user in users]

    def get_by_id(self, user_id: int) -> UserRead | None:
        user = self.session.query(User).filter(User.id == user_id).first()
        return UserRead.model_validate(user) if user else None

    def get_by_name(self, name: str) -> UserRead | None:
        user = self.session.query(User).filter(User.name == name).first()
        return UserRead.model_validate(user) if user else None

    def upsert(self, payload: UserUpsert) -> UserRead:
        user = self.session.query(User).filter(User.name == payload.name).first()
        data = payload.model_dump()

        if user is None:
            user = User(**data)
            self.session.add(user)
        else:
            for field, value in data.items():
                setattr(user, field, value)

        self.session.commit()
        self.session.refresh(user)
        return UserRead.model_validate(user)

    def delete_by_name(self, name: str) -> bool:
        user = self.session.query(User).filter(User.name == name).first()
        if user is None:
            return False

        self.session.delete(user)
        self.session.commit()
        return True


class ApplicationAccessor:
    def __init__(self, session: Session):
        self.session = session

    def upsert(self, payload: ApplicationCreate) -> ApplicationRead:
        application = self.session.query(Application).filter(
            Application.name == payload.name,
            Application.ipo_name == payload.ipo_name,
        ).first()

        data = payload.model_dump()
        if application is None:
            application = Application(**data)
            self.session.add(application)
        else:
            application.user_id = payload.user_id
            application.name = payload.name
            application.ipo = payload.ipo
            application.share_type = payload.share_type
            application.button = payload.button

        self.session.commit()
        self.session.refresh(application)
        return ApplicationRead.model_validate(application)

    def list_all(self) -> list[ApplicationRead]:
        applications = self.session.query(Application).all()
        return [ApplicationRead.model_validate(application) for application in applications]


class ResultAccessor:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> list[ResultRead]:
        results = self.session.query(Result).all()
        return [ResultRead.model_validate(result) for result in results]

    def get_by_id(self, result_id: int) -> ResultRead | None:
        result = self.session.query(Result).filter(Result.id == result_id).first()
        return ResultRead.model_validate(result) if result else None

    def get_or_create(self, payload: ResultCreate) -> ResultRead:
        result = self.session.query(Result).filter(
            Result.company_share_id == payload.company_share_id
        ).first()

        if result is None:
            result = Result(**payload.model_dump())
            self.session.add(result)
            self.session.commit()
            self.session.refresh(result)

        return ResultRead.model_validate(result)


class UserResultAccessor:
    def __init__(self, session: Session):
        self.session = session

    def get_by_applicant_form_id(self, applicant_form_id: int) -> UserResultRead | None:
        user_result = self.session.query(UserResult).filter(
            UserResult.applicant_form_id == applicant_form_id
        ).first()
        return UserResultRead.model_validate(user_result) if user_result else None

    def upsert(
        self,
        create_payload: UserResultCreate,
        update_payload: UserResultUpdate,
    ) -> UserResultRead:
        user_result = self.session.query(UserResult).filter(
            UserResult.applicant_form_id == create_payload.applicant_form_id
        ).first()

        if user_result is None:
            user_result = UserResult(**create_payload.model_dump())
            self.session.add(user_result)
        else:
            user_result.applied_date = update_payload.applied_date
            user_result.amount = update_payload.amount
            user_result.reason_or_remark = update_payload.reason_or_remark
            user_result.meroshare_remark = update_payload.meroshare_remark
            user_result.received_kitta = update_payload.received_kitta
            user_result.value = update_payload.value

        self.session.commit()
        self.session.refresh(user_result)
        return UserResultRead.model_validate(user_result)


class ReportAccessor:
    def __init__(self, session: Session):
        self.session = session

    def list_user_stats(self) -> list[UserStats]:
        users = self.session.query(User).all()
        user_stats = []

        for user in users:
            app_count = self.session.query(UserResult).filter(UserResult.user_id == user.id).count()
            allotted = self.session.query(UserResult).filter(
                UserResult.user_id == user.id,
                UserResult.received_kitta > 0,
            ).count()
            user_stats.append(
                UserStats(
                    id=user.id,
                    name=user.name,
                    boid=user.boid,
                    applications=app_count,
                    allotted=allotted,
                )
            )

        return user_stats

    def get_user_details(self, user_id: int) -> tuple[UserRead | None, list[UserCompanyResult]]:
        user = self.session.query(User).filter(User.id == user_id).first()
        if user is None:
            return None, []

        results = self.session.query(UserResult, Result).join(
            Result, UserResult.result_id == Result.id
        ).filter(UserResult.user_id == user_id).all()

        result_items = [
            UserCompanyResult(
                company_name=result.company_name,
                script=result.script,
                share_type=result.share_type_name,
                applied_date=user_result.applied_date,
                amount=user_result.amount,
                received_kitta=user_result.received_kitta or 0,
                status=user_result.value,
                meroshare_remark=user_result.meroshare_remark,
                reason_or_remark=user_result.reason_or_remark,
                value=user_result.value,
            )
            for user_result, result in results
        ]

        return UserRead.model_validate(user), result_items

    def list_company_stats(self) -> list[CompanyStats]:
        results = self.session.query(Result).all()
        company_items = []

        for result in results:
            total_apps = self.session.query(UserResult).filter(
                UserResult.result_id == result.id
            ).count()
            allotted_apps = self.session.query(UserResult).filter(
                UserResult.result_id == result.id,
                UserResult.received_kitta > 0,
            ).count()
            company_items.append(
                CompanyStats(
                    id=result.id,
                    company_name=result.company_name,
                    script=result.script,
                    share_type=result.share_type_name,
                    total_applications=total_apps,
                    allotted=allotted_apps,
                    created_at=result.created_at,
                )
            )
        company_items = sorted(company_items, key=lambda x: x.created_at or "", reverse=True)
        return company_items

    def get_company_details(self, company_id: int) -> tuple[ResultRead | None, list[CompanyUserResult]]:
        result = self.session.query(Result).filter(Result.id == company_id).first()
        if result is None:
            return None, []

        user_results = self.session.query(UserResult, User).join(
            User, UserResult.user_id == User.id
        ).filter(UserResult.result_id == company_id).all()

        items = [
            CompanyUserResult(
                user_name=user.name,
                boid=user.boid,
                applied_date=user_result.applied_date,
                amount=user_result.amount,
                received_kitta=user_result.received_kitta or 0,
                status=user_result.value,
                meroshare_remark=user_result.meroshare_remark,
                reason_or_remark=user_result.reason_or_remark,
                value=user_result.value,
            )
            for user_result, user in user_results
        ]

        return ResultRead.model_validate(result), items

    def list_results(
        self,
        user_id: int | None = None,
        company_id: int | None = None,
        sort_by: str = "applied_date",
        sort_order: str = "desc",
    ) -> list[ResultFeedItem]:
        query = self.session.query(UserResult, Result, User).join(
            Result, UserResult.result_id == Result.id
        ).join(User, UserResult.user_id == User.id)

        if user_id:
            query = query.filter(UserResult.user_id == user_id)
        if company_id:
            query = query.filter(UserResult.result_id == company_id)

        sorters = {
            "company_name": Result.company_name,
            "user_name": User.name,
            "received_kitta": UserResult.received_kitta,
            "applied_date": UserResult.applied_date,
        }
        sort_column = sorters.get(sort_by, UserResult.applied_date)
        order_fn = desc if sort_order == "desc" else asc
        query = query.order_by(order_fn(sort_column))

        results = query.all()
        return [
            ResultFeedItem(
                user_name=user.name,
                boid=user.boid,
                company_name=result.company_name,
                script=result.script,
                share_type=result.share_type_name,
                applied_date=user_result.applied_date,
                amount=user_result.amount,
                received_kitta=user_result.received_kitta or 0,
                status=user_result.value,
                meroshare_remark=user_result.meroshare_remark,
            )
            for user_result, result, user in results
        ]

    def list_applications(
        self,
        user_id: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[ApplicationFeedItem]:
        query = self.session.query(Application, User).join(
            User, Application.user_id == User.id
        )

        if user_id:
            query = query.filter(Application.user_id == user_id)

        sorters = {
            "user_name": User.name,
            "ipo_name": Application.ipo_name,
            "ipo": Application.ipo,
            "share_type": Application.share_type,
            "button": Application.button,
            "created_at": Application.created_at,
        }
        sort_column = sorters.get(sort_by, Application.created_at)
        order_fn = desc if sort_order == "desc" else asc
        query = query.order_by(order_fn(sort_column))

        applications = query.all()
        return [
            ApplicationFeedItem(
                id=application.id,
                user_id=user.id,
                user_name=user.name,
                boid=user.boid,
                ipo_name=application.ipo_name,
                ipo=application.ipo,
                share_type=application.share_type,
                button=application.button,
                created_at=application.created_at,
            )
            for application, user in applications
        ]

    def get_user_applications(self, user_id: int) -> tuple[UserRead | None, list[UserApplicationItem]]:
        user = self.session.query(User).filter(User.id == user_id).first()
        if user is None:
            return None, []

        applications = self.session.query(Application).filter(
            Application.user_id == user_id
        ).order_by(desc(Application.created_at)).all()

        items = [
            UserApplicationItem(
                ipo_name=application.ipo_name,
                ipo=application.ipo,
                share_type=application.share_type,
                button=application.button,
                created_at=application.created_at,
            )
            for application in applications
        ]

        return UserRead.model_validate(user), items


class DatabaseAccessor:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserAccessor(session)
        self.applications = ApplicationAccessor(session)
        self.results = ResultAccessor(session)
        self.user_results = UserResultAccessor(session)
        self.reports = ReportAccessor(session)


@contextmanager
def get_accessor():
    with get_db() as session:
        yield DatabaseAccessor(session)
