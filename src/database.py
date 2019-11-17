
import util
from sqlalchemy import create_engine
from sqlalchemy.orm import scored_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine( util.get_config( app ), convert_unicode=True )

