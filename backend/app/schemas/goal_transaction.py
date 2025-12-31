from pydantic import BaseModel, ConfigDict


class GoalTransactionBase(BaseModel):
    goal_id: int
    transaction_id: int


class GoalTransactionCreate(GoalTransactionBase):
    pass


class GoalTransactionRead(GoalTransactionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
