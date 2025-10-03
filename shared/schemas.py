from pydantic import BaseModel

class RegistrationNew(BaseModel):
    registration_id: int
    user_id: int
    user_email: str
    course_id: int

class RegistrationPaid(BaseModel):
    registration_id: int
    user_id: int
    user_email: str
    course_id: int
    amount: float

class RegistrationCompleted(BaseModel):
    registration_id: int
    user_id: int
    user_email: str
    course_id: int
