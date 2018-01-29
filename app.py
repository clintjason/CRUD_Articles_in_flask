from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
#from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
app.secret_key = 'secret1234'

#config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_DB'] = 'db_name'
app.config['MYSQL_USER'] = 'db_user'
app.config['MYSQL_PASSWORD'] = 'db_pwd'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#init MySQL
mysql = MySQL(app)

#Articles = Articles()

@app.route('/')
def home():
    return render_template('home.html')

# Check if user logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please login', 'danger')
			return redirect(url_for('login'))
	return wrap

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/articles')
@is_logged_in
def articles():
    # create cursor
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles")

    if result > 0:
        articles = cur.fetchall()
        return render_template('articles.html', articles = articles)
    else:
        msg = "No articles found"
        return render_template('articles.html', msg = msg)

    cur.close()

@app.route('/article/<string:id>')
@is_logged_in
def article(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    if result > 0:
        article = cur.fetchone()
        return render_template('article.html', article = article)
    else:
        msg = "Missing Article"
        return render_template('article.html', msg = msg)


class RegisterForm(Form):
    name    =   StringField('Name', [validators.Length(min=4, max=25)])
    username    = StringField('Username', [validators.Length(min=4, max=25)])
    email       = StringField('Email Address', [validators.Length(min=6, max=35)])
    password    = PasswordField('Password', [ validators.DataRequired(),
                                              validators.EqualTo('confirm', message= 'passwords do not match')])

    confirm = PasswordField('Confirm Password')

@app.route('/register', methods = ['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        #Get data from form
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        #create cursor
        cur = mysql.connection.cursor()

        #execute query
        cur.execute("INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)", (name, email, username, password))

        #commit to db
        mysql.connection.commit()

        #close connection
        cur.close()

        flash('You are now registered and can log in', 'success')   #send feedback messages

        return redirect(url_for('home'))
    return render_template('register.html', form = form)


class LoginForm(Form):
    username = StringField('username',[validators.DataRequired()])
    password = StringField('password',[validators.DataRequired()])


@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm(request.form)
    if request.method=='POST' and form.validate():
        username = form.username.data
        password_candidate = form.password.data
        app.logger.info(username)
        app.logger.info(password_candidate)

        #create cursor
        cur = mysql.connection.cursor()
        result = cur.execute("select * from users WHERE username = %s", [username])
        if result > 0:
            data = cur.fetchone()
            password = data['password']
            user_id = data['id']
            if sha256_crypt.verify(password_candidate,password):
               #app.logger.info('PASSWORD MATCHED')
               session['logged_in'] = True
               session['username'] = username
               session['_id'] = user_id

               flash('Logged in', 'success')
               return redirect(url_for('dashboard'))
            else:
                #app.logger.info('PASSWORD NOT MATCHED')
                error = "Invalid Password"
                return render_template('login.html', error = error, form = form )
            #close connection
            cur.close()
        else:
            #app.logger.info('NO USER')
            error = "Unknown User"
            return render_template('login.html', error = error, form = form)

    return render_template('login.html', form = form)


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are logged out', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    # create cursor
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles")

    if result > 0:
        articles = cur.fetchall()
        return render_template('dashboard.html', articles = articles)
    else:
        msg = "No articles found"
        return render_template('dashboard.html', msg = msg)

    cur.close()


# create an article class
class ArticleForm(Form):
    title    =   StringField('title', [validators.Length(min=4, max=200)])
    body   = TextAreaField('body', [validators.Length(min=10)])

@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method=='POST' and form.validate():
        title = form.title.data
        body = form.body.data

        cur = mysql.connection.cursor()

        result = cur.execute("INSERT INTO articles (title, body, author) VALUES(%s, %s, %s)", [title, body, session['username']])

        mysql.connection.commit()

        cur.close()

        flash('Article created', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form = form)

@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    if result > 0:
        article = cur.fetchone()

        form = ArticleForm(request.form)

        #populate form

        form.title.data = article['title']
        form.body.data = article['body']

        #the form is filled or not and posted again
        if request.method=='POST' and form.validate():
            # get the posted input values
            title = request.form['title']
            body = request.form['body']

            cur = mysql.connection.cursor()

            result = cur.execute("UPDATE articles SET title = %s, body = %s WHERE id = %s ", [title, body, id])

            mysql.connection.commit()

            cur.close()

            flash('Article Updated', 'success')

            return redirect(url_for('dashboard'))

        return render_template('edit_article.html', form = form)

    else:
        msg = "Unable to Edit Article"
        return render_template('dashboard.html', msg = msg)

@app.route('/delete_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def delete_article(id):
    cur = mysql.connection.cursor()
    result = cur.execute("DELETE FROM articles WHERE id = %s ", [id])

    mysql.connection.commit()

    cur.close()

    flash('Article Deleted', 'success')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':   # if the current file is the program file being executed
    #app.run(host='127.0.0.1')
    app.run(debug=True)