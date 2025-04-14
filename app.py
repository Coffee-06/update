from flask import Flask, render_template, request, redirect, url_for, session, flash
import uuid
from werkzeug.utils import secure_filename
import os
from ultralytics import YOLO
import bcrypt
from collections import Counter
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

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
                return redirect(url_for('validate_policy'))
            else:
                flash("Invalid email or password.", "error")
                
        else:
            flash("Database connection failed. Please try again later.", "error")

    return render_template('login.html')

@app.route('/validate_policy', methods=['GET', 'POST'])
def validate_policy():
    if 'user_email' not in session:
        flash("Please login to access this page.", "error")
        return redirect(url_for('login'))
    if request.method == 'POST':
        policy_number = request.form.get('policy_number')

        if not policy_number:
            flash("Please enter a policy number.", "error")
            return redirect(url_for('validate_policy'))

        db = connect_to_mongo()
        user_email = session.get('user_email')
        policy = db.policy_info.find_one({
            "policy_number":policy_number,
            "email":user_email
        })
        
        if policy:
            expiry_date_str = policy.get("expiry_date")
            expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
            current_date = datetime.now()

            if current_date < expiry_date:
              
                return render_template("policy_result.html", policy=policy, valid=True)
            else:
               
                return render_template("policy_result.html", policy=policy, valid=False)
        else:
            flash("Policy number not found!", "error")
            return redirect(url_for('validate_policy'))

    return render_template("validate_policy.html")

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    flash("You have been logged out.", "info")
    
    return redirect(url_for('login'))


model_path = r"D:\Vehicle Damage Detection\models\model weights\best.pt"
model = YOLO(model_path)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')


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
        
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        upload_path = os.path.join(STATIC_DIR, unique_filename)
        file.save(upload_path)
        session['uploaded_image'] = unique_filename 

        return redirect(url_for('estimate'))  

    return render_template('dashboard.html')

@app.route('/estimate')
def estimate():
    if 'user_email' not in session or 'uploaded_image' not in session:
        flash("Please upload an image first.", "error")
        return redirect(url_for('dashboard'))
    user_email = session['user_email']
    user_data = db.user_info.find_one({'email': user_email})
    current_date = datetime.now().strftime("%d-%m-%Y")
    image_path = os.path.join(STATIC_DIR, session['uploaded_image'])
    result = model(image_path)
    detected_objects = result[0].boxes
    class_ids = [box.cls.item() for box in detected_objects]
    class_counts = Counter(class_ids)

    detected_image_path = os.path.join(STATIC_DIR, 'detected_image.jpg')
    result[0].save(detected_image_path)
    
    part_prices = get_part_prices(session['user_email'], class_counts)
    session['latest_part_prices'] = part_prices

    return render_template('estimate.html',
                           Name=user_data.get('name'),
                           current_date=current_date,
                           original_image= session['uploaded_image'],
                           detected_image='detected_image.jpg',
                           part_prices=part_prices,
                           parts=list(part_prices.keys()),
                           vehicle_id=user_data.get('vehicle_id', 'N/A'),
                           brand=user_data.get('car_brand', 'N/A'),
                           model=user_data.get('model', 'N/A'),
                           total=sum(d['total'] for d in part_prices.values()))


@app.route('/request_claim', methods=['POST'])
def request_claim():
    if 'user_email' not in session:
        flash('Login to request claim', 'error')
        return redirect(url_for('login'))

    user_email = session['user_email']
    user_data = db.user_info.find_one({'email': user_email})
    part_prices = session.get('latest_part_prices', {})
    current_date = datetime.now().strftime("%d-%m-%Y")
    if not part_prices:
        flash('No damage detected to claim.', 'error')
        return redirect(url_for('dashboard'))

    total_amount = sum(p['total'] for p in part_prices.values())

    db.claims.insert_one({
        'user_email': user_email,
        'vehicle_id': user_data['vehicle_id'],
        'policy_number': user_data['policy_number'],
        'claim_status': 'pending verification',
        'estimated_parts': part_prices,
        'total_amount': total_amount,
        "damage_image": session.get('uploaded_image')
    })

    flash("Claim request sent successfully!", "success")
    return render_template('estimate.html',
                           Name=user_data.get('name'),
                           current_date=current_date,
                           original_image= session['uploaded_image'],
                           detected_image='detected_image.jpg',
                           part_prices=part_prices,
                           parts=list(part_prices.keys()),
                           vehicle_id=user_data.get('vehicle_id', 'N/A'),
                           brand=user_data.get('car_brand', 'N/A'),
                           model=user_data.get('model', 'N/A'),
                           total=sum(d['total'] for d in part_prices.values()))
   
@app.route('/clear_session',methods=['GET','POST'])
def clear_session():
    session.clear()
    flash("Logged Out Successfully.", "success")
    return redirect(url_for('admin_login'))


@app.route('/admin/claims')
def admin_claims():
    print("SESSION STATE:", session)
    if not session.get('admin_logged_in'):
        flash("You must log in as admin to access this page.", "error")
        return redirect(url_for('admin_login'))
    claims = db.claims.find().sort('_id',-1)
    return render_template('admin_claims.html', claims=claims)

@app.route('/admin/claim_action/<claim_id>/<action>')
def claim_action(claim_id, action):
    if not session.get('admin_logged_in'):
       flash("Unauthorized access", "error")
       return redirect(url_for('admin_login'))

    if action not in ['approved', 'rejected']:
        flash('Invalid action.', 'error')
        return redirect(url_for('admin_claims'))

    db.claims.update_one({'_id': ObjectId(claim_id)}, {'$set': {'claim_status': action}})
    flash(f'Claim {action} successfully.', 'success')
    return redirect(url_for('admin_claims'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        print(f"User trying to login: {user_id}") 

        admin = db.admin_users.find_one({'user_id': user_id})
        print(f"Admin from DB: {admin}") 

        if admin:
            print("Comparing passwords now...")
            match = bcrypt.checkpw(password.encode('utf-8'), admin['password'].encode('utf-8'))
            print(f"Password match? {match}") 
        else:
            print("Admin user not found!")

        if admin and bcrypt.checkpw(password.encode('utf-8'), admin['password'].encode('utf-8')):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_claims')) 
        else:
            flash('Invalid admin credentials', 'error')

    return render_template('admin_login.html')



@app.route('/my_claims')
def my_claims():
    if 'user_email' not in session:
        flash('Login to view claims', 'error')
        return redirect(url_for('login'))

    user_email = session['user_email']
    claims_cursor= db.claims.find({'user_email': user_email})
    claims=list(claims_cursor)
    return render_template('my_claims.html', claims=claims)


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