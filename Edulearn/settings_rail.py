from Edulearn.settings import *
from decouple import config

SECRET_KEY = config('SECRET_KEY')

ALLOWED_HOSTS = ['web-production-42de.up.railway.app']