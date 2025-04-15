from Edulearn.settings import *
from decouple import config

SECRET_KEY = config('SECRET_KEY')

ALLOWED_HOSTS = ['web-production-52b0.up.railway.app']