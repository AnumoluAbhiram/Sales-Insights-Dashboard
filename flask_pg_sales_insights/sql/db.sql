-- Drop & recreate schema for a clean start
DROP VIEW IF EXISTS monthly_revenue;
DROP FUNCTION IF EXISTS set_updated_at();
DROP FUNCTION IF EXISTS customer_revenue_rank();
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

-- Core tables
CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  price NUMERIC(10,2) NOT NULL CHECK (price >= 0)
);

CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  customer_id INT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  order_date DATE NOT NULL DEFAULT CURRENT_DATE,
  status TEXT NOT NULL DEFAULT 'paid',
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE order_items (
  order_id INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id INT NOT NULL REFERENCES products(id),
  quantity INT NOT NULL CHECK (quantity > 0),
  unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
  PRIMARY KEY (order_id, product_id)
);

-- Useful indexes
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_products_category ON products(category);

-- Trigger to refresh updated_at on orders
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_orders_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- View for monthly revenue
CREATE VIEW monthly_revenue AS
SELECT date_trunc('month', o.order_date) AS month,
       ROUND(SUM(oi.quantity * oi.unit_price)::numeric, 2) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
GROUP BY 1
ORDER BY 1;

-- Function using window function for ranking customers by revenue
CREATE OR REPLACE FUNCTION customer_revenue_rank()
RETURNS TABLE(customer_id INT, customer_name TEXT, revenue NUMERIC, rnk INT)
LANGUAGE sql AS $$
  SELECT c.id, c.name, SUM(oi.quantity * oi.unit_price) AS revenue,
         RANK() OVER (ORDER BY SUM(oi.quantity * oi.unit_price) DESC) AS rnk
  FROM customers c
  JOIN orders o ON o.customer_id = c.id
  JOIN order_items oi ON oi.order_id = o.id
  GROUP BY c.id, c.name;
$$;

-- Sample data
INSERT INTO customers (name, email) VALUES
('Aarav Patel', 'aarav@example.com'),
('Isha Sharma', 'isha@example.com'),
('Vikram Rao', 'vikram@example.com'),
('Sneha Gupta', 'sneha@example.com'),
('Rohan Kumar', 'rohan@example.com'),
('Meera Iyer', 'meera@example.com'),
('Aditya Verma', 'aditya@example.com'),
('Kavya Nair', 'kavya@example.com'),
('Rahul Singh', 'rahul@example.com'),
('Nisha Reddy', 'nisha@example.com');

INSERT INTO products (name, category, price) VALUES
('Wireless Mouse', 'Accessories', 799.00),
('Mechanical Keyboard', 'Accessories', 3499.00),
('27\" Monitor', 'Displays', 16999.00),
('USB-C Hub', 'Accessories', 1299.00),
('Laptop Stand', 'Accessories', 999.00),
('Noise-cancel Headphones', 'Audio', 4999.00),
('Webcam 1080p', 'Accessories', 2199.00),
('Portable SSD 1TB', 'Storage', 6999.00);

-- Orders across several months
INSERT INTO orders (customer_id, order_date, status) VALUES
(1, '2025-01-15', 'paid'),
(2, '2025-01-25', 'paid'),
(3, '2025-02-05', 'paid'),
(4, '2025-02-18', 'paid'),
(5, '2025-03-10', 'paid'),
(1, '2025-03-22', 'paid'),
(6, '2025-04-09', 'paid'),
(7, '2025-04-20', 'paid'),
(8, '2025-05-12', 'paid'),
(9, '2025-05-25', 'paid'),
(10,'2025-06-03', 'paid'),
(2, '2025-06-14', 'paid'),
(3, '2025-07-01', 'paid'),
(4, '2025-07-18', 'paid'),
(5, '2025-08-02', 'paid');

-- Order items
-- We use product price as unit_price for simplicity; in real life copy price at order-time
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 2, 799.00),
(1, 4, 1, 1299.00),
(2, 2, 1, 3499.00),
(2, 7, 1, 2199.00),
(3, 3, 1, 16999.00),
(3, 6, 1, 4999.00),
(4, 5, 2, 999.00),
(5, 8, 1, 6999.00),
(6, 1, 1, 799.00),
(6, 2, 1, 3499.00),
(7, 6, 1, 4999.00),
(8, 3, 1, 16999.00),
(9, 4, 2, 1299.00),
(10, 5, 3, 999.00),
(11, 7, 1, 2199.00),
(12, 8, 1, 6999.00),
(13, 1, 1, 799.00),
(13, 6, 1, 4999.00),
(14, 2, 2, 3499.00),
(15, 3, 1, 16999.00);
