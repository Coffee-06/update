"""from flask import Flask, render_template, request, redirect, url_for, session, flash
import config
from werkzeug.utils import secure_filename
import os
from ultralytics import YOLO
import bcrypt
from collections import Counter
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)
print("SECRET_KEY:", os.getenv('SECRET_KEY')) 
app.secret_key = os.getenv('SECRET_KEY')

def connect_to_mongo():
    client = MongoClient('mongodb://localhost:27017/')
    db = client['car_damage_detection']  
    return db


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        email = request.form.get('email')
        vehicle_id = request.form.get('vehicleId')
        contact_number = request.form.get('phoneNumber')
        policy_number = request.form.get('policy_number')
        car_brand = request.form.get('carBrand')
        model = request.form.get('carModel')
        

        if not all([name, password, email, vehicle_id, contact_number,policy_number, car_brand, model]):
            flash("All fields are required!", "error")
            return render_template('signup.html')
        

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db = connect_to_mongo()
        user_info_collection = db['user_info']
        if user_info_collection.find_one({'email':email}):
            flash("Email already exists.")
            return render_template('signup.html')

        
        user_info_collection.insert_one({
            "name":name,
            "password":hashed_password,
            "email":email,
            "vehicle_id":vehicle_id,
            "contact_number":contact_number,
            "policy_number":policy_number,
            "car_brand":car_brand,
            "model":model
        })
        flash("Signup successful!", "success")
        return redirect(url_for('dashboard'))
            
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        print(f"Email : {email}")
        print(f"Password : {password}")

        if not email or not password:
            flash("Email and password are required!", "error")
            return render_template('login.html')

        db = connect_to_mongo()
        user_info = db.user_info.find_one({"email":email})

        if user_info:
            stored_password = user_info["password"]
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                session['email'] = email  # Store session
                flash("Login successful!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid email or password.", "error")
                
        else:
            flash("Database connection failed. Please try again later.", "error")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_email', None)
    flash("You have been logged out.", "info")
    
    return redirect(url_for('login'))


model_path = r"D:\Vehicle Damage Detection\models\model weights\best.pt"
model = YOLO(model_path)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'email' not in session:
        flash('Login to view dashboard','error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files.get('image')
        if not file:
            flash('Please upload an image.', 'error')
            return render_template('dashboard.html')

        filename = secure_filename(file.filename)
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            flash('Invalid file type. Please upload an image.', 'error')
            return render_template('dashboard.html')
        
        image_path = os.path.join('D:/Vehicle Damage Detection/static', 'uploaded_image.jpg')
        print("File uploaded successfully")
        
        file.save(image_path)
        result = model(image_path)
        detected_objects = result[0].boxes
        class_ids = [box.cls.item() for box in detected_objects]
        class_counts = Counter(class_ids)
        print(f"Class counts : {class_counts}")
        detected_image_path = os.path.join('D:/Vehicle Damage Detection/static', 'detected_image.jpg')
        result[0].save(detected_image_path)
        print(f"Detected image path : {detected_image_path}")
        # Get the user's email from session
        user_email = session.get('user_email')
        print(user_email)
        if not user_email:
            flash('You need to log in to get an estimate.', 'error')
            return redirect(url_for('login'))
        part_prices = get_part_prices(user_email, class_counts)
        return render_template('estimate.html', original_image='uploaded_image.jpg', detected_image='detected_image.jpg', part_prices=part_prices)

    return render_template('dashboard.html')


def get_part_prices(email, class_counts):
    db = connect_to_mongo()
    user_data = db.user_info.find_one({"email":email})
    
    if not user_data:
        print("User not found")
        return {}

    car_brand = user_data['car_brand']
    car_model = user_data['model']
    prices = {}
    
    for class_id, count in class_counts.items():
        part_name = get_part_name_from_id(class_id)
                
        if part_name:
                    
            price_data = db.car_models.find_one({
                 "brand": {"$regex": f"^{car_brand}$", "$options": "i"},
                 "model": {"$regex": f"^{car_model}$", "$options": "i"},
                 "part": {"$regex": f"^{part_name}$", "$options": "i"}
               
            })
            print(f"Price data : {price_data}")
            if price_data:
                price_per_part = price_data['price']
                total_price = price_per_part * count
                prices[part_name] = {'count': count, 'price': price_per_part, 'total': total_price}
    print(f"Prices : {prices}")
    return prices
        
def get_part_name_from_id(class_id):
    class_names = ['Bonnet', 'Bumper', 'Dickey', 'Door', 'Fender', 'Light', 'Windshield']
    if 0 <= class_id < len(class_names):
        return class_names[int(class_id)]
    return None

if __name__ == '__main__':
    app.run(debug=True)"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
import config
import mysql.connector as connector
from werkzeug.utils import secure_filename
import os
from ultralytics import YOLO
import bcrypt
from collections import Counter
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)
print("SECRET_KEY:", os.getenv('SECRET_KEY')) 
app.secret_key = os.getenv('SECRET_KEY')

def connect_to_mongo():
    client = MongoClient('mongodb://localhost:27017/')
    db = client['car_damage_detection']  
    return db
try:
    db = connect_to_mongo()
    print("Collections:", db.list_collection_names())
except Exception as e:
    print("MongoDB connection error:", e)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        email = request.form.get('email')
        vehicle_id = request.form.get('vehicleId')
        contact_number = request.form.get('phoneNumber')
        policy_number = request.form.get('policy_number')
        car_brand = request.form.get('carBrand')
        model = request.form.get('carModel')
        

        if not all([name, password, email, vehicle_id, contact_number,policy_number, car_brand, model]):
            flash("All fields are required!", "error")
            return render_template('signup.html')
        

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db = connect_to_mongo()
        user_info_collection = db['user_info']
        if user_info_collection.find_one({'email':email}):
            flash("Email already exists.")
            return render_template('signup.html')

        
        user_info_collection.insert_one({
            "name":name,
            "password":hashed_password,
            "email":email,
            "vehicle_id":vehicle_id,
            "contact_number":contact_number,
            "policy_number":policy_number,
            "car_brand":car_brand,
            "model":model
        })
        flash("Signup successful!", "success")
        return redirect(url_for('dashboard'))
            
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        print(f"Email : {email}")
        print(f"Password : {password}")

        if not email or not password:
            flash("Email and password are required!", "error")
            return render_template('login.html')

        db = connect_to_mongo()
        user_info = db.user_info.find_one({"email":email})

        if user_info:
            stored_password = user_info["password"]
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                session['user_email'] = email  # Store session
                flash("Login successful!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid email or password.", "error")
                
        else:
            flash("Database connection failed. Please try again later.", "error")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_email', None)
    flash("You have been logged out.", "info")
    
    return redirect(url_for('login'))


model_path = r"D:\Vehicle Damage Detection\models\model weights\best.pt"
model = YOLO(model_path)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_email' not in session:
       flash('Login to view dashboard', 'error')
       return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files.get('image')
        if not file:
            flash('Please upload an image.', 'error')
            return render_template('dashboard.html')

        filename = secure_filename(file.filename)
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            flash('Invalid file type. Please upload an image.', 'error')
            return render_template('dashboard.html')
        
        image_path = os.path.join('D:/Vehicle Damage Detection/static', 'uploaded_image.jpg')
        print("File uploaded successfully")
        
        file.save(image_path)
        result = model(image_path)
        detected_objects = result[0].boxes
        class_ids = [box.cls.item() for box in detected_objects]
        class_counts = Counter(class_ids)
        print(f"Class counts : {class_counts}")
        detected_image_path = os.path.join('D:/Vehicle Damage Detection/static', 'detected_image.jpg')
        result[0].save(detected_image_path)
        print(f"Detected image path : {detected_image_path}")
        # Get the user's email from session
        user_email = session.get('user_email')
        print(user_email)
        if not user_email:
            flash('You need to log in to get an estimate.', 'error')
            return redirect(url_for('login'))
        part_prices = get_part_prices(user_email, class_counts)
        return render_template('estimate.html', original_image='uploaded_image.jpg', detected_image='detected_image.jpg', part_prices=part_prices)

    return render_template('dashboard.html')


def get_part_prices(email, class_counts):
    db = connect_to_mongo()
    user_data = db.user_info.find_one({"email":email})
    
    if not user_data:
        print("User not found")
        return {}

    car_brand = user_data['car_brand']
    car_model = user_data['model']

    prices = {}
    for class_id, count in class_counts.items():
        part_name = get_part_name_from_id(class_id)
                
        if part_name:
                    
            price_data = db.car_models.find_one({
                 "brand": {"$regex": f"^{car_brand}$", "$options": "i"},
                 "model": {"$regex": f"^{car_model}$", "$options": "i"},
                 "part": {"$regex": f"^{part_name}$", "$options": "i"}
               
            })
            print(f"Price data : {price_data}")
            if price_data:
                price_per_part = price_data['price']
                total_price = price_per_part * count
                prices[part_name] = {'count': count, 'price': price_per_part, 'total': total_price}
    print(f"Prices : {prices}")
    return prices
        
def get_part_name_from_id(class_id):
    class_names = ['Bonnet', 'Bumper', 'Dickey', 'Door', 'Fender', 'Light', 'Windshield']
    if 0 <= class_id < len(class_names):
        return class_names[int(class_id)]
    return None

if __name__ == '__main__':
    app.run(debug=True)