from datetime import datetime, timezone

from sqlalchemy import Sequence
from sqlmodel import Field, SQLModel

url_id_seq = Sequence("urls_id_seq")

class URL(SQLModel, table=True):
    __tablename__ = "urls"
    
    id : int | None = Field(primary_key=True,default=None,sa_column_args={"server_default": url_id_seq.next_value()})
    code: str = Field(max_length=10,index=True,unique=True,nullable=False)
    long_url: str = Field(max_length=2048,nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at: datetime | None = Field(default=None, nullable=True)
    is_active: bool = Field(default=True, nullable=False)
    click_count: int = Field(default=0, nullable=False)
    
    
    