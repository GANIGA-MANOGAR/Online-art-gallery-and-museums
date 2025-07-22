from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

# Initialize Flask app
app = Flask(__name__)

upload_folder = os.path.join('static', 'uploads')
os.makedirs(upload_folder, exist_ok=True)
app.config['UPLOAD_FOLDER'] = upload_folder
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif'}

# Configuration
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config["DEBUG"] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:krishika@localhost/online'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')

    def _repr_(self):
        return f"<User {self.username}>"

class Exhibition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True) 
   

# Define the Artwork model
class Artwork(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    artist = db.Column(db.String(255))
    year = db.Column(db.String(10))
    description = db.Column(db.Text)
    image_filename = db.Column(db.String(255))
    category = db.Column(db.String(255))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']




# Ensure admin exists
def ensure_admin_exists():
    with app.app_context():
        admin = db.session.query(User).filter_by(username='admin').first()
        if not admin:
            hashed_pw = generate_password_hash('password123')
            admin = User(username='admin', password=hashed_pw, role='admin', email='admin@example.com')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created!")

ensure_admin_exists()

# Admin login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = db.session.query(User).filter_by(username=username).first()

        if admin and check_password_hash(admin.password, password):
            session['user'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials!', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

# User registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        user = db.session.query(User).filter_by(username=username).first()
        if user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Admin dashboard route
@app.route('/admin')
def admin_dashboard():
    if not session.get('user'):
        return redirect(url_for('login'))
    return render_template('admin.html')

# Home page route
@app.route('/', methods=['GET'])
def home():
    if 'user' in session:
        artworks = Artwork.query.all()
        return render_template('index.html', artworks=artworks)
    else:
        return redirect(url_for('login'))

# Gallery page with category filtering
@app.route('/gallery')
def gallery():
    categories = ['Painting', 'Drawing', 'Sculpture', 'Photography', 'Digital Art']
    artworks_by_category = {}

    for category in categories:
        folder_name = category.lower().replace(' ', '_')
        folder_path = os.path.join(app.static_folder, 'images', folder_name)
        if os.path.exists(folder_path):
            images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
            artworks_by_category[category] = images
        else:
            artworks_by_category[category] = []

    return render_template('gallery.html', artworks_by_category=artworks_by_category)

# Add Image route
@app.route('/add_image/<category>', methods=['POST'])
def add_image(category):
    if 'image' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['image']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        category_folder = category.lower().replace(' ', '_')
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], category_folder)
        os.makedirs(save_path, exist_ok=True)
        file_path = os.path.join(save_path, filename)
        file.save(file_path)
        flash('Image successfully uploaded')
        return redirect(url_for('gallery'))
    else:
        flash('Allowed image types are - png, jpg, jpeg, gif')
        return redirect(request.url)

# Museum page
@app.route('/museum')
def museum():
    return render_template('museum.html')

# Artwork detail page
@app.route('/artwork/<int:artwork_id>')
def artwork_detail(artwork_id):
    artwork = Artwork.query.get(artwork_id)
    return render_template('artwork_detail.html', artwork=artwork)

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# Route to add new artwork
@app.route('/add_artwork', methods=['GET', 'POST'])
def add_artwork():
    if request.method == 'POST':
        try:
            category = request.form['category']
            title = request.form['title']
            artist = request.form['artist']
            year = request.form['year']
            description = request.form['description']
            image = request.files['image']

            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                new_artwork = Artwork(
                    category=category,
                    title=title,
                    artist=artist,
                    year=year,
                    description=description,
                    image_filename=filename
                )
                db.session.add(new_artwork)
                db.session.commit()
                flash('Artwork added successfully!', 'success')
                return redirect(url_for('gallery'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding artwork: {e}', 'danger')
    return render_template('add_artwork.html')


@app.route('/events')
def view_events():
    events = [
        {
            'name': 'Art Exhibition 2025',
            'date': '2025-06-15',
            'location': 'Gallery Hall A',
            'description': 'An exhibition showcasing modern art.'
        },
        {
            'name': 'Sculpture Workshop',
            'date': '2025-07-20',
            'location': 'Workshop Room B',
            'description': 'Hands-on sculpture creation session.'
        }
    ]
    return render_template('view_events.html', events=events)

@app.route('/museum/collection')
def museum_collection():
    return render_template('museum_collection.html')

@app.route('/membership')
def membership():
    return render_template('membership.html')

@app.route('/shop')
def shop():
    return render_template('shop.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/our_collection', methods=['GET', 'POST'])
def our_collection():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        flash('Thank you for your message!', 'success')
        return redirect('/our_collection')
    return render_template('our_collection.html')

@app.route('/membership/signup/<plan>', methods=['GET', 'POST'])
def membership_signup(plan):
    return render_template('signup.html', plan=plan)

@app.route('/submit_inquiry', methods=['POST'])
def submit_inquiry():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    return redirect(url_for('thank_you'))

@app.route('/buy/<int:product_id>', methods=['POST'])
def buy(product_id):
    try:
        # Implement your purchase logic here, e.g., deduct inventory, process payment
        flash('Purchase successful!', 'success')
        return redirect(url_for('gallery'))  # Redirect to the gallery or confirmation page
    except Exception as e:
        flash(f'Purchase failed: {e}', 'danger')
        return redirect(url_for('gallery'))



@app.route('/checkout/<int:product_id>')
def checkout(product_id):
    product = get_product_by_id(product_id)
    if product:
        return render_template('checkout.html', product=product)
    else:
        flash('Product not found!', 'danger')
        return redirect(url_for('shop'))


@app.route('/process_checkout', methods=['POST'])
def process_checkout():
    product_id = request.form['product_id']
    name = request.form['name']
    email = request.form['email']
    address = request.form['address']
    quantity = request.form['quantity']
    return redirect(url_for('order_confirmation'))

@app.route('/order_confirmation')
def order_confirmation():
    return "Thank you for your order! We will process it shortly."

def get_product_by_id(product_id):
    return Artwork.query.get(product_id)

# Define the products (for demonstration)
products = [
    {
        'id': 1,
        'title': 'Sunset Over The Hills',
        'price': 49.99,
        'image': 'images/art1.jpeg'
    },
    {
        'id': 2,
        'title': 'Abstract Dreams',
        'price': 39.99,
        'image': 'images/art2.jpeg'
    },
    {
        'id': 3,
        'title': 'Vintage Portrait',
        'price': 59.99,
        'image': 'images/art3.jpeg'
    }
]

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('File uploaded successfully!', 'success')
            return redirect(url_for('uploaded_file', filename=filename))
        else:
            flash('Invalid file type or no file selected.', 'danger')
            return redirect(request.url)
    return render_template('upload.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return render_template('display.html', filename=filename)

@app.route('/display/<filename>')
def display_image(filename):
    return render_template('display.html', filename=filename)

@app.route('/view_artworks')
def view_artworks():
      # Logic to display artworks
      return render_template('view_artworks.html')


@app.route('/view_exhibitions')
def view_exhibitions():
      exhibitions = [
          {
              'title': 'Soundscapes of the Future',
              'location': 'Chennai Art Museum',
              'start_date': '2025-06-01',
              'end_date': '2025-07-15',
              'description': 'An immersive audio experience showcasing futuristic sound art.'
          },
          {
              'title': 'Echoes of Tradition',
              'location': 'Chennai Art Museum',
              'start_date': '2025-08-01',
              'end_date': '2025-09-10',
              'description': 'Exploring the rich heritage of traditional music through interactive exhibits.'
          }
      ]
      return render_template('view_exhibitions.html', exhibitions=exhibitions)



if __name__ == '__main__':
    app.run(debug=True)