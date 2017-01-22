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

DROP TABLE IF EXISTS entry_tag;
CREATE TABLE entry_tag (
    entry_id integer NOT NULL,
    tag_id integer NOT NULL,
    PRIMARY KEY(entry_id, tag_id),
    FOREIGN KEY(entry_id) REFERENCES entries(id),
    FOREIGN KEY(tag_id) REFERENCES tags(id)
);

DROP TABLE IF EXISTS tags;
CREATE TABLE tags (
    id integer PRIMARY KEY autoincrement,
    name varchar(16) NOT NULL UNIQUE
);

DROP TABLE IF EXISTS comments;
CREATE TABLE comments (
    id integer PRIMARY KEY autoincrement,
    author varchar(32) NOT NULL,
    email varchar(32) NOT NULL,
    content text NOT NULL,
    status varchar(16) NOT NULL,
    created_at integer NOT NULL,
    entry_id integer NOT NULL,
    parent integer,
    root integer,
    FOREIGN KEY(entry_id) REFERENCES entries(id)
);
