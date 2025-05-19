from database.database import Base, DIR_PATH, get_db, engine
from sqlalchemy.sql.expression import  text
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    dp = Column(String(255), nullable=False)
    boid = Column(String(255), nullable=False)
    passsword = Column(String(255), nullable=False)
    crn = Column(String(255), nullable=False)
    pin = Column(String(255), nullable=False)
    account = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True),server_default=text('CURRENT_TIMESTAMP'), nullable=False)

    user_results = relationship("UserResult", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")

class Result(Base):
    __tablename__ = 'results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    script = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    user_results = relationship("UserResult", back_populates="result", cascade="all, delete-orphan")


class UserResult(Base):
    """
    This table associates users with results and allows you to store a user-specific
    value (e.g., a score or status) for each result.
    """
    __tablename__ = 'user_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    result_id = Column(Integer, ForeignKey('results.id'), nullable=False)
    type = Column(String(255), nullable=False)
    value = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="user_results")
    result = relationship("Result", back_populates="user_results")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'result_id','type', name='uq_user_result_type'),
    )
    


class Application(Base):
    __tablename__ = 'applications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(255), nullable=False)
    ipo_name = Column(String(255), nullable=False)
    ipo = Column(String(255), nullable=False)
    share_type = Column(String(255), nullable=False)
    button = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True),server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    
    user = relationship("User", back_populates="applications")

    __table_args__ = (UniqueConstraint('name', 'ipo', name='uq_name_ipo'),)

    
# with open(f"{DIR_PATH}/Source Files/dataBase.txt", "r", encoding="utf-8") as fp:
#     lines = fp.read().splitlines()
#     with get_db() as db:
#         for line in lines:
#             data = line.split(",")
#             if len(data) != 7:
#                 continue
#             user = User(name=data[0], boid=data[2], dp=data[1], passsword=data[3], crn=data[4], pin=data[5], account=data[6])
#             db.add(user)
#             db.commit()
Base.metadata.create_all(engine)