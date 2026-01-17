from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from config import *
from db import mysql
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config.from_object('config')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
mysql.init_app(app)

s = URLSafeTimedSerializer(SECRET_KEY)

@app.route('/')
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    return render_template('index.html', products=products)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form['name']
        email=request.form['email']
        password=generate_password_hash(request.form['password'])
        cur=mysql.connection.cursor()
        cur.execute("INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",(name,email,password))
        mysql.connection.commit()
        flash("Registered Successfully")
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']
        cur=mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s",(email,))
        user=cur.fetchone()
        if user and check_password_hash(user[3],password):
            session['user_id']=user[0]
            session['role']=user[4]
            return redirect('/dashboard')
        flash("Invalid Credentials")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    products=cur.fetchall()
    return render_template('dashboard.html',products=products)

@app.route('/add_to_cart/<pid>')
def add_to_cart(pid):
    uid=session['user_id']
    cur=mysql.connection.cursor()
    cur.execute("INSERT INTO cart(user_id,product_id) VALUES(%s,%s)",(uid,pid))
    mysql.connection.commit()
    flash("Added to cart")
    return redirect('/dashboard')

@app.route('/favourite/<pid>')
def favourite(pid):
    uid=session['user_id']
    cur=mysql.connection.cursor()
    cur.execute("INSERT INTO favourites(user_id,product_id) VALUES(%s,%s)",(uid,pid))
    mysql.connection.commit()
    flash("Added to favourites")
    return redirect('/dashboard')

@app.route('/favourites')
def favourites():
    if 'user_id' not in session:
        return redirect('/login')
    
    uid = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT favourites.id, products.name, products.price, products.image
        FROM favourites 
        JOIN products 
        ON favourites.product_id = products.id
        WHERE favourites.user_id = %s
    """, (uid,))
    
    items = cur.fetchall()
    return render_template('favourites.html', items=items)
@app.route("/remove_fav/<int:fid>")
def remove_fav(fid):
    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM favourites WHERE id=%s AND user_id=%s", (fid, session['user_id']))
    mysql.connection.commit()
    cur.close()

    flash("Removed from favourites")
    return redirect("/favourites")


@app.route('/cart')
def cart():
    uid=session['user_id']
    cur=mysql.connection.cursor()
    cur.execute("""SELECT cart.id,products.name,products.price 
                   FROM cart JOIN products ON cart.product_id=products.id
                   WHERE cart.user_id=%s""",(uid,))
    items=cur.fetchall()
    return render_template('cart.html',items=items)

@app.route('/place_order')
def place_order():
    uid=session['user_id']
    cur=mysql.connection.cursor()
    cur.execute("SELECT product_id FROM cart WHERE user_id=%s",(uid,))
    products=cur.fetchall()

    for p in products:
        cur.execute("INSERT INTO orders(user_id,product_id,quantity) VALUES(%s,%s,1)",(uid,p[0]))
        cur.execute("UPDATE products SET stock=stock-1 WHERE id=%s",(p[0],))
    
    cur.execute("DELETE FROM cart WHERE user_id=%s",(uid,))
    mysql.connection.commit()
    flash("Order Placed")
    return redirect('/orders')

@app.route('/orders')
def orders():
    uid = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT orders.id,
               products.name,
               orders.status,
               orders.order_date,
               products.price
        FROM orders 
        JOIN products 
        ON orders.product_id = products.id
        WHERE orders.user_id=%s
    """, (uid,))
    
    orders = cur.fetchall()
    cur.close()

    today = datetime.today().strftime("%d-%m-%Y")

    return render_template('orders.html', orders=orders, today=today)

@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=="POST":
        email=request.form['email']
        token=s.dumps(email)
        reset_url=url_for('reset',token=token,_external=True)
        flash("Copy this Reset Link: "+ reset_url)
        return redirect('/login')
    return render_template('forgot.html')

@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    email=s.loads(token,max_age=600)
    if request.method=="POST":
        password=generate_password_hash(request.form['password'])
        cur=mysql.connection.cursor()
        cur.execute("UPDATE users SET password=%s WHERE email=%s",(password,email))
        mysql.connection.commit()
        flash("Password Reset Successfully")
        return redirect('/login')
    return render_template('reset.html')
@app.route("/remove_from_cart/<int:cid>")
def remove_from_cart(cid):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (cid, session['user_id']))
    mysql.connection.commit()
    cur.close()
    flash("Item removed from cart")
    return redirect("/cart")




# ---------------- ADMIN ----------------
@app.route('/admin')
def admin_home():
    if session.get('role')!='admin':
        return redirect('/')
    return render_template('admin_dashboard.html')

@app.route('/admin/products')
def admin_products():
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    products=cur.fetchall()
    return render_template('admin_products.html',products=products)

@app.route('/admin/add',methods=['GET','POST'])
def admin_add():
    if session.get('role')!='admin':
        return redirect('/')

    if request.method=='POST':
        name=request.form['name']
        desc=request.form['desc']
        price=request.form['price']
        rating=request.form['rating']
        stock=request.form['stock']

        image = request.files['image']
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cur=mysql.connection.cursor()
        cur.execute("INSERT INTO products(name,description,price,rating,stock,image) VALUES(%s,%s,%s,%s,%s,%s)",
                    (name,desc,price,rating,stock,filename))
        mysql.connection.commit()

        flash("Product Added Successfully")
        return redirect('/admin/products')

    return render_template('admin_add_product.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
    
app.run(debug=True)
