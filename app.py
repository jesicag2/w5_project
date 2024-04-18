from flask import Flask, jsonify, request
# Flask - everything we need for running flask
# jsonify - transform python objects to be displayed the browser or postman
# request - HTTP requset handling
from flask_sqlalchemy import SQLAlchemy
# SQLAlchemy is the Object Relational Mapper - any functionality for converting python classes to SQL tables
from sqlalchemy import select, delete
# select is going to grab tables we want to query
# delete is going to delete stuff from a specific table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
# DeclarativeBase - provides base model functionality to create SQL tables from Python Classes
# All classes that become tables will inherit this class
# Mapped - provides a column for our table while declaring the python type and an attribute for the class
# python types are converted to SQL types like varchar, int, etc..
# mapped_column - set our column and allow us to set any constraints for that column
# Session - Session class for creating session objects to make changes to the database
from flask_marshmallow import Marshmallow
# Marshmallow - serializes and deserializes JSON objects so we can interact with them as python dictionaries
from marshmallow import fields, ValidationError
# fields allows us to create a data shape or type for incoming data to adhere to
# ValidationError - a raised error when a object coming through a request does not adhere to the 
# structure set by the marshmallow schema
from typing import List
# give us a type of empty list that we can use as placeholder for a collection of relationships
# creating a one to many relationship, where One customer would have a collection or List of Orders
import datetime 
# give us access to the date type from datetime module

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:jesica123@localhost/e_commerce_project"
app.json.sort_keys = False


class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class=Base)
ma = Marshmallow(app)

# python classes ===> sql tables
class Customer(Base):
    __tablename__ = "Customers"
    customer_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    email: Mapped[str] = mapped_column(db.String(320))
    phone: Mapped[str] = mapped_column(db.String(15))
    # manage relationships between customers table and orders
    orders: Mapped[List["Order"]] = db.relationship(back_populates="customer")

# association table between order and product
order_product = db.Table(
    "Order_Product",
    Base.metadata,
    db.Column("order_id", db.ForeignKey("Orders.order_id"), primary_key=True),
    db.Column("product_id", db.ForeignKey("Products.product_id"), primary_key=True)
)

class Order(Base):
    __tablename__ = "Orders"
    order_id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date] = mapped_column(db.Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey("Customers.customer_id"))  
    
    customer: Mapped["Customer"] = db.relationship(back_populates="orders")
    products: Mapped[List["Product"]] = db.relationship(secondary=order_product)

class Product(Base):
    __tablename__ = "Products"
    product_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    price: Mapped[float] = mapped_column(db.Float, nullable=False)

with app.app_context():
    db.create_all()


class CustomerSchema(ma.Schema):
    customer_id = fields.Integer(required=False)
    name = fields.String(required=True)
    email = fields.String(required=True)
    phone = fields.String(required=True)

    class Meta:
        fields = ("customer_id", "name", "email", "phone")

# Schema for many customers with a required id
class CustomersSchema(ma.Schema):
    customer_id = fields.Integer(required=True)
    name = fields.String(required=True)
    email = fields.String(required=True)
    phone = fields.String(required=True)

    class Meta:
        fields = ("customer_id", "name", "email", "phone")

# instantiate our CustomerSchemas
# GET, POST, PUT, DELETE
# Retrieve, Create, Update, Delete
customer_schema = CustomerSchema() # Create, Update, Get One
customers_schema = CustomersSchema(many=True) # Get all
# No schema for delete because theres not transfer of data through an HTTP request

# Product Schema
class ProductSchema(ma.Schema):
    product_id = fields.Integer(required=False)
    name = fields.String(required=True)
    price = fields.Float(required=True)

    class Meta:
        fields = ("product_id", "name", "price")

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)




class OrderSchema(ma.Schema):
    order_id = fields.Integer(required=False)
    date = fields.Date(required=True)
    customer_id = fields.Integer(required=True)

    class Meta:
        fields = ("order_id", "date", "customer_id")
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)




@app.route("/")
def home():
    return "Welcome to our really nice ecommerce project. Its Niiiiiice!"

@app.route("/customers", methods = ["GET"])
def get_cutomers():
    query = select(Customer)
    result = db.session.execute(query).scalars()
    customers = result.all()

    return customers_schema.jsonify(customers)

@app.route("/customers", methods = ["POST"])
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)

    except ValidationError as err:
        return jsonify(err.messages), 400
    
    with Session(db.engine) as session:
        new_customer = Customer(name=customer_data["name"], email=customer_data["email"], phone=customer_data["phone"])
        session.add(new_customer) 
        session.commit()

    return jsonify({"message": "New customer added succesfully"}), 201

@app.route("/customers/<int:id>", methods=["PUT"])
def update_customer(id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(Customer).filter(Customer.customer_id==id)
            result = session.execute(query).scalars().first()
            if result is None:
                return jsonify({"error": "Customer Not Found"}), 404
            customer = result

            try:
                customer_data = customer_schema.load(request.json)
            except ValidationError as err:
                return jsonify(err.messages), 400
            
            for field, value in customer_data.items():
                setattr(customer, field, value)
            
            session.commit()
    return jsonify({"message": "Customer details updated succesfully"}), 200

@app.route("/customers/<int:id>", methods = ["DELETE"])
def delete_customer(id):
    delete_statement = delete(Customer).where(Customer.customer_id==id)

    with db.session.begin():
        result = db.session.execute(delete_statement)

        if result.rowcount == 0:
            return jsonify({"error": "Customer not found"}), 404
        
        return jsonify({"message": "Customer removed sucessfully"}), 200


@app.route("/products", methods=["GET"])
def get_products():
    query = select(Product)
    result = db.session.execute(query).scalars()
    products = result.all()

    return products_schema.jsonify(products)

@app.route('/products', methods=["POST"])
def add_product():
    try: 
        product_data = product_schema.load(request.json)

    except ValidationError as err:
        return jsonify(err.messages), 400
    
    with Session(db.engine) as session:
        with session.begin():
            new_product = Product(name=product_data['name'], price=product_data['price'] )
            session.add(new_product)
            session.commit()

    return jsonify({"message": "Product added successfully"}), 201

@app.route("/products/<int:id>", methods=["PUT"])
def update_product(id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(Product).filter(Product.product_id==id)
            result = session.execute(query).scalars().first()
            if result is None:
                return jsonify({"error": "Product not found"}), 404
            product = result

            try:
                product_data = product_schema.load(request.json)
            except ValidationError as err:
                return jsonify(err.messages), 400
            
            for field, value in product_data.items():
                setattr(product, field, value )
            
            session.commit()
            return jsonify({"message": "Product successfully updated!"}), 200

@app.route("/products/<int:id>", methods=["DELETE"])
def delete_product(id):
    delete_statement = delete(Product).where(Product.product_id==id)
    with db.session.begin():
        result = db.session.execute(delete_statement)
        if result.rowcount == 0:
            return jsonify({"error": "Product Not found"}), 404
        
        return jsonify({"message": "Product removed successfully"}), 200
    
# # Get product by name
# @app.route("/products/by-name/<string:thing>", methods = ["GET"])
# def get_product_by_name(thing):
#     # name = request.args.get('name')
#     search = f"%{thing}%"
#     query = select(Product).where(Product.name.like(search)).order_by(Product.price.asc())
#     # SELECT * FROM products where name LIKE %nameofproduct%
#     products = db.session.execute(query).scalars().all()

#     return products_schema.jsonify(products)


@app.route("/orders", methods=["GET"])
def get_orders():
    query = select(Order)
    result = db.session.execute(query).scalars()
    orders = result.all()

    return orders_schema.jsonify(orders)

@app.route("/orders", methods=["POST"])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    with Session(db.engine) as session:
        with session.begin():
            new_order = Order(date=order_data['date'], customer_id=order_data['customer_id'])
            session.add(new_order)
            session.commit()

    return jsonify({"message": "New order has been added successfully"}), 201

@app.route("/orders/<int:customer_id>", methods=["GET"])
def get_order_by_customer(customer_id):
    query = select(Order).where(Order.customer_id==customer_id)
    orders = db.session.execute(query).scalars()
    print(orders)
    
    if orders: 
        return orders_schema.jsonify(orders)
    
    else:
        return jsonify({"message": f"Customer ID {customer_id} does not exist!"})




if __name__ == "__main__":
    app.run(debug=True)