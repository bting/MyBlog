# all the imports
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash

# create our little application
app = Flask(__name__)
app.config.from_object(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Close the databse again at the end of request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print 'Initialized the databse.'


@app.route('/')
def show_entries():
    db = get_db()
    cur = db.execute("select id, title, text from entries where status='published' order by id desc")
    entries = cur.fetchall()
    return render_template('show_entries.html', entries=entries)

@app.route('/categories')
def show_categories():
    db = get_db()
    cur = db.execute("SELECT e.id, title, name as category FROM entries e, categories c WHERE e.category_id=c.id order by e.id desc")
    entries = cur.fetchall()
    categories = {}
    for e in entries:
        if e['category'] not in categories:
            categories[e['category']] = []
        categories[e['category']].append(e)
    return render_template('show_categories.html', categories=categories)

@app.route('/admin')
def administration():
    if not session.get('logged_in'):
        abort(401)
    return render_template('admin/main.html')

@app.route('/admin/drafts')
def draft_list():
    db = get_db()
    cur = db.execute("select id, title from entries where status='draft' order by id desc")
    drafts = cur.fetchall()
    return render_template('admin/show_drafts.html', drafts=drafts)

def _insert_tag_if_not_exist(tag):
    db = get_db()
    db.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", [tag])
    db.commit()

def _add_entry_tag(entry_id, tag):
    _insert_tag_if_not_exist(tag)
    db = get_db()
    db.execute("INSERT INTO entry_tag(entry_id, tag_id) SELECT (?), id FROM tags WHERE name=(?)", [entry_id, tag])
    db.commit()

def _remove_entry_tag(entry_id, tag):
    db = get_db()
    db.execute("DELETE FROM entry_tag WHERE entry_id=(?) AND tag_id IN (SELECT id FROM tags WHERE name=(?))", [entry_id, tag])
    db.commit()

def _load_tags(entry_id):
    db = get_db()
    cur = db.execute("SELECT name FROM entry_tag et, tags t WHERE t.id=et.tag_id AND et.entry_id=(?)", [entry_id])
    tags = cur.fetchall()
    return tags

@app.route('/admin/new_draft', methods=['POST', 'GET'])
def add_draft():
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'POST':
        status = 'published' if 'publish' in request.form else 'draft'
        #TODO: Wrap the following queries in a database transaction
        db = get_db()
        db.execute("insert into entries (title, text, status, category_id) values (?, ?, ?, ?)",
                   [request.form['title'], request.form['text'], status, request.form["category"]])
        db.commit()
        cur = db.execute("SELECT last_insert_rowid() as id")
        id= cur.fetchone()
        tags = [x.strip() for x in request.form['tags'].split(',')]
        for tag in tags:
            _add_entry_tag(id['id'], tag)
        flash('New entry was successfully posted')
        if status == 'published':
            return redirect(url_for('post_list'))
        else:
            return redirect(url_for('draft_list'))
    db = get_db()
    cur = db.execute("SELECT id, name from categories")
    categories = cur.fetchall()
    category_id = 1
    return render_template('admin/write_entry.html', categories=categories, category_id=category_id)

def _update_tags(entry_id, old_tags, new_tags):
    old_tag_set = set(old_tags)
    for tag in new_tags:
        if tag not in old_tag_set:
            _add_entry_tag(entry_id, tag)
    new_tag_set = set(new_tags)
    for tag in old_tags:
        if tag not in new_tag_set:
            _remove_entry_tag(entry_id, tag)

@app.route('/admin/edit_draft/<int:draft_id>', methods=['POST', 'GET'])
def edit_draft(draft_id):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    cur = db.execute("SELECT name FROM entry_tag et, tags t WHERE et.entry_id=(?) AND et.tag_id=t.id", [draft_id])
    old_tags = [x['name'] for x in cur.fetchall()]
    if request.method == 'POST':
        status = 'published' if 'publish' in request.form else 'draft'
        query = "UPDATE entries SET title=?,text=?,status=?, category_id=? WHERE id=?"
        db.execute(query, [request.form['title'], request.form['text'], status, request.form["category"], draft_id])
        db.commit()
        new_tags = [x.strip() for x in request.form['tags'].split(',')]
        _update_tags(draft_id, old_tags, new_tags)
        flash('Entry was successfully updated')
        if status == 'published':
            return redirect(url_for('post_list'))
        else:
            return redirect(url_for('draft_list'))
    cur = db.execute('SELECT id, title, text, category_id from entries where id=(?)', [draft_id])
    entry = cur.fetchone()
    category_id = entry["category_id"]
    cur = db.execute("SELECT id, name from categories")
    categories = cur.fetchall()
    return render_template('admin/write_entry.html', entry=entry, categories=categories, category_id=category_id, tags=old_tags)

@app.route('/admin/delete_entry/<int:entry_id>', methods=['GET'])
def delete_entry(entry_id):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute("DELETE FROM entries WHERE id=(?)", [entry_id])
    db.commit()
    flash('Entry was successfully deleted')
    return redirect(redirect_url())

@app.route('/admin/posts', methods=['GET'])
def post_list():
    db = get_db()
    cur = db.execute("SELECT id, title FROM entries WHERE status='published' ORDER BY id DESC")
    posts = cur.fetchall()
    return render_template('admin/show_posts.html', posts=posts)

@app.route('/admin/categories')
def category_list():
    db = get_db()
    cur = db.execute("select id, name from categories order by id desc")
    categories = cur.fetchall()
    return render_template('admin/show_categories.html', categories=categories)

@app.route('/admin/new_category', methods=['POST', 'GET'])
def add_category():
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'POST':
        db = get_db()
        db.execute("insert into categories (name) values (?)", [request.form['name']])
        db.commit()
        flash('New category was successfully added')
        return redirect(url_for('category_list'))
    return render_template('admin/write_category.html')

@app.route('/admin/delete_category/<int:category_id>', methods=['GET'])
def delete_category(category_id):
    if not session.get('logged_in'):
        abort(401)
    if category_id == 1:
        flash('Can not delete uncategorized')
        return redirect(url_for('category_list'))
    db = get_db()
    db.execute("UPDATE entries SET category_id=1 WHERE id=?", [category_id])
    db.execute("DELETE FROM categories WHERE id=(?)", [category_id])
    db.commit()
    flash('Category was successfully deleted')
    return redirect(url_for('category_list'))

@app.route('/admin/edit_category/<int:category_id>', methods=['POST', 'GET'])
def edit_category(category_id):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    if request.method == 'POST':
        query = "UPDATE categories SET name=? WHERE id=?"
        db.execute(query, [request.form['name'], category_id])
        db.commit()
        flash("category was successfully updated")
        return redirect(url_for('category_list'))
    cur = db.execute('SELECT id, name FROM categories WHERE id=(?)', [category_id])
    category = cur.fetchone()
    return render_template('admin/write_category.html', category=category)

@app.route('/admin/tags')
def tag_list():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    cur = db.execute("SELECT id, name FROM tags")
    tags = cur.fetchall()
    return render_template('admin/show_tags.html', tags=tags)

def _add_tag(name):
    db = get_db()
    db.execute('INSERT INTO tags (name) VALUES (?)', [name])
    db.commit()

@app.route('/admin/new_tag', methods=['POST', 'GET'])
def add_tag():
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'POST':
        _add_tag(request.form['name'])
        flash('New tag was successfully added')
        return redirect(url_for('tag_list'))
    return render_template('admin/write_tag.html')

@app.route('/admin/delete_tag/<int:tag_id>', methods=['GET'])
def delete_tag(tag_id):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('DELETE FROM tags WHERE id=(?)', [tag_id])
    db.commit()
    flash('Tag was successfully deleted')
    return redirect(url_for('tag_list'))

@app.route('/admin/edit_tag/<int:tag_id>', methods=['POST', 'GET'])
def edit_tag(tag_id):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    if request.method == 'POST':
        query = 'UPDATE tags SET name=? WHERE id=?'
        db.execute(query, [request.form['name'], tag_id])
        db.commit()
        flash("Tag was successfully updated")
        return redirect(url_for('tag_list'))
    cur = db.execute('SELECT id, name FROM tags WHERE id=(?)', [tag_id])
    tag = cur.fetchone()
    return render_template('admin/write_tag.html', tag=tag)

@app.route('/view/<int:post_id>', methods=['GET'])
def view_entry(post_id):
    db = get_db()
    cur = db.execute('select title, text from entries where id=(?)', [post_id])
    entry = cur.fetchone()
    return render_template('show_entry.html', entry=entry)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)
