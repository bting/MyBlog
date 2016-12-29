DROP TABLE IF EXISTS entries;
CREATE TABLE entries (
	id integer PRIMARY KEY autoincrement,
	title text NOT NULL,
	'text' text NOT NULL,
	status varchar(16) NOT NULL,
	category_id integer NOT NULL,
	FOREIGN KEY(category_id) REFERENCES categories(id)
);

DROP TABLE IF EXISTS categories;
CREATE TABLE categories (
	id integer PRIMARY KEY autoincrement,
	name varchar(16) NOT NULL
);
INSERT INTO categories(name) VALUES('Uncategorized');