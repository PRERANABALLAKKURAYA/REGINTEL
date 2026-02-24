from pydantic import BaseModel

class AuthorityBase(BaseModel):
    name: str
    country: str
    website_url: str

class AuthorityCreate(AuthorityBase):
    pass

class AuthorityUpdate(AuthorityBase):
    pass

class Authority(AuthorityBase):
    id: int

    class Config:
        from_attributes = True
