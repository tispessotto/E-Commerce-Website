from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import *
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import os
import time
import webbrowser

app = Flask(__name__)

app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///e-commerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
YOUR_DOMAIN = 'http://localhost:4242'
base_url = "http://127.0.0.1:5000"
db = SQLAlchemy(app)
bootstrap = Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    products_selling = relationship("Product", back_populates="seller")


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    price = db.Column(db.String(250), nullable=False)
    photo_url = db.Column(db.String(250), nullable=False)
    seller = relationship("User", back_populates="products_selling")
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"))


db.create_all()


def load_dot_env():
    """ Helper funtion that parses and loads local .env file.
    STRIPE_SECRET_KEY=sk_...
    """
    with open('.env', encoding='utf-8') as dot_env_file:
        for line in iter(lambda: dot_env_file.readline().strip(), ''):
            if not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value


load_dot_env()
stripe.api_key = os.environ['STRIPE_SECRET_KEY']


@app.route("/")
def home():
    user_id = None
    if current_user.is_authenticated:
        user_id = current_user.id
    products = Product.query.all()
    return render_template("index.html", products=products, checkout=checkout, user_id=user_id,
                           logged_in=current_user.is_authenticated)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for("home"))
            else:
                flash("Password invalid.")
                return redirect(url_for("login"))
        else:
            flash("Email not yet registered.")
            return redirect(url_for("login"))
    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(password=form.password.data, salt_length=8)
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_password,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))

    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


@app.route("/checkout/<int:product_id>")
def checkout(product_id):
    product = Product.query.get(product_id)
    s = stripe.checkout.Session.create(
        success_url=f'{base_url}/order/success',  # success redirect does not imply paid!
        cancel_url=f'{base_url}/order/cancel',
        line_items=[
            {
                'price_data': {
                    'currency': 'USD',
                    'product_data': {
                        'name': product.name,
                    },

                    'unit_amount': int(product.price) * 100
                },
                "quantity": 1,
            },
        ],
        mode='payment',
        customer_email=None,
        expires_at=int(time.time()) + 3600  # 1 hour expiry
    )
     webbrowser.open(s['url'])
    #print(s)
    #session_id = s['id']   
    #checkout_sess = stripe.checkout.Session.retrieve(session_id)
    #print('status        :', checkout_sess['status'])  # open, complete, expired
    #print('payment_status:', checkout_sess['payment_status'])  # paid, unpaid, no_payment_required


@app.route("/order/success")
def checkout_succeed():
    return render_template("success.html", logged_in=current_user.is_authenticated)


@app.route("/order/cancel")
def checkout_canceled():
    return render_template("cancel.html", logged_in=current_user.is_authenticated)


if __name__ == '__main__':
    app.run(debug=True)
