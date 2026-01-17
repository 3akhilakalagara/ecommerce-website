

create database if not exists ecommerce5;
use ecommerce5;




create table if not exists users(
 id int auto_increment primary key,
 name varchar(100),
 email varchar(100) unique,
 password varchar(255),
 role enum('user','admin') default 'user'
);




create table if not exists products(
 id int auto_increment primary key,
 name varchar(100),
 description text,
 price decimal(10,2),
 rating decimal(3,2),
 stock int,
 image varchar(255)
);




create table if not exists cart(
 id int auto_increment primary key,
 user_id int,
 product_id int,
 quantity int default 1
);




create table if not exists favourites(
 id int auto_increment primary key,
 user_id int,
 product_id int
);



create table if not exists orders(
 id int auto_increment primary key,
 user_id int,
 product_id int,
 quantity int,
 status varchar(50) default 'Processing'
);

update users set role='admin' where email='yhemalatha50@gmail.com';
ALTER TABLE orders
ADD COLUMN order_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;



