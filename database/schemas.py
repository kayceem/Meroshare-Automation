from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModelSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    name: str
    dp: str | int
    boid: str | int
    passsword: str
    crn: str
    pin: str
    account: str
    apply_ipo: bool = False


class UserUpsert(UserBase):
    pass


class UserRead(ORMModelSchema, UserBase):
    id: int
    created_at: datetime


class ApplicationBase(BaseModel):
    name: str
    ipo_name: str
    ipo: str
    share_type: str
    button: str


class ApplicationCreate(ApplicationBase):
    user_id: int


class ApplicationRead(ORMModelSchema, ApplicationCreate):
    id: int
    created_at: datetime


class ResultCreate(BaseModel):
    company_share_id: int
    script: str
    share_type_name: str
    company_name: str


class ResultRead(ORMModelSchema, ResultCreate):
    id: int
    created_at: datetime


class UserResultCreate(BaseModel):
    user_id: int
    result_id: int
    applicant_form_id: int
    applied_date: str | None = None
    amount: str | None = None
    reason_or_remark: str | None = None
    meroshare_remark: str | None = None
    received_kitta: int | None = None
    type: str
    value: str


class UserResultUpdate(BaseModel):
    applied_date: str | None = None
    amount: str | None = None
    reason_or_remark: str | None = None
    meroshare_remark: str | None = None
    received_kitta: int | None = None
    value: str


class UserResultRead(ORMModelSchema, UserResultCreate):
    id: int
    created_at: datetime


class UserStats(BaseModel):
    id: int
    name: str
    boid: str
    applications: int
    allotted: int


class UserCompanyResult(BaseModel):
    company_name: str
    script: str
    share_type: str
    applied_date: str | None = None
    amount: str | None = None
    received_kitta: int = 0
    status: str
    meroshare_remark: str | None = None
    reason_or_remark: str | None = None
    value: str


class CompanyStats(BaseModel):
    id: int
    company_name: str
    script: str
    share_type: str
    total_applications: int
    allotted: int
    created_at: datetime | None = None


class CompanyUserResult(BaseModel):
    user_name: str
    boid: str
    applied_date: str | None = None
    amount: str | None = None
    received_kitta: int = 0
    status: str
    meroshare_remark: str | None = None
    reason_or_remark: str | None = None
    value: str


class ResultFeedItem(BaseModel):
    user_name: str
    boid: str
    company_name: str
    script: str
    share_type: str
    applied_date: str | None = None
    amount: str | None = None
    received_kitta: int = 0
    status: str
    meroshare_remark: str | None = None


class ApplicationFeedItem(BaseModel):
    id: int
    user_id: int
    user_name: str
    boid: str
    ipo_name: str
    ipo: str
    share_type: str
    button: str
    created_at: datetime


class UserApplicationItem(BaseModel):
    ipo_name: str
    ipo: str
    share_type: str
    button: str
    created_at: datetime
