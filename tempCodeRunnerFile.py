from flask import Flask, render_template, request, redirect, url_for, session, flash
import config
import mysql.connector as connector
from werkzeug.utils import secure_filename
import os
from ultralytics import YOLO
import bcrypt
from collections import Counter
from dotenv import load_dotenv


load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

