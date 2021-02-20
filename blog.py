from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
# decoratorlar icin gerekli
from functools import wraps
import datetime     
from datetime import timedelta
# Kullanıcı Giriş Decorator Dashboard sayfası görüntüleme kontrolü
# fonksiyonun içine fonksiyon gönderilmiş. def dashboard gönderilecek
def login_required(f): 
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session: # session içerisinde logged_in var mı yok mu bakıyor. bi nevi true false olmasına bakıyor.
            return f(*args, **kwargs) # dashboard url normal bir şekilde çağırılıyor.
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.","danger")
            return redirect(url_for("login")) # sonrasında login sayfasına yönlendirilir.
    return decorated_function
# Kullanıcı Kayıt Formu
class RegisterForm(Form): # Form class yapısından register form class yapısı türetiliyor. (inheritance)
    name = StringField("İsim Soyisim",validators=[validators.Length(min = 4,max = 25)])
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min = 5,max = 35)])
    email = StringField("Email Adresi",validators=[validators.Email(message = "Lütfen Geçerli Bir Email Adresi Girin...")])
    password = PasswordField("Parola:",validators=[
        validators.DataRequired(message = "Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname = "confirm",message="Parolanız Uyuşmuyor...")
    ])
    confirm = PasswordField("Parola Doğrula")

# Kullanıcı Giriş Formu    
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")


app = Flask(__name__)
app.secret_key= "blog"


app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blog"
# veriler dict formatında oluyor.
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


# Register
@app.route("/register",methods = ["GET","POST"]) # GET ve POST request alabilir url.
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data # formun içindeki name değerinin datası alınıp, name değerine eşitleniyor.
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data) # veri şifrelenerek alınıyor.
        status = "inactive"
        role = "user"
        # wrongpasstimeDefault = datetime.datetime(1993, 18, 4, 00, 00, 00)
        # cursor mysql veritabanında işlem sağlamamızı yarayan yapı. bu yapı sayesinde sql sorgularını çalıştırabiliyoruz.
        cursor = mysql.connection.cursor() 

        sorgu = "Insert into users(name,email,username,password,status,role,wrongpasstime) VALUES(%s,%s,%s,%s,%s,%s,('2021-02-21 01:34:00'))"

        cursor.execute(sorgu,(name,email,username,password,status,role))
        mysql.connection.commit() # veritabanında değişiklik yaptığımız vakit commit etmek zorundayız.

        cursor.close()
        flash("Başarıyla ön kayıt oldunuz. Kaydınız onay sürecindedir.","success") # Mesaj ve kategori flash mesajı ekrana çıkart.
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)

#Login işlemi
@app.route("/login",methods =["GET","POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST":
       username = form.username.data
       password_entered = form.password.data

       cursor = mysql.connection.cursor()

       sorgu = "Select * From users where username = %s"

       result = cursor.execute(sorgu,(username,)) # demet yapıda olması için tek değişken olsa da virgül kullanıldı.

       if result > 0:
           data = cursor.fetchone() # kullanıcının bütün bilgileri alınıyor.
           real_password = data["password"] # kullanıcının şifresi değişkene atandı.

           if sha256_crypt.verify(password_entered,real_password):
               new_wrongpassnumber = 0
               userid = data["id"]
               flash("Başarıyla Giriş Yaptınız.","success")
               sorgu5 = "Update users Set wrongpassnumber = %s where id = %s "
               cursor = mysql.connection.cursor()
               cursor.execute(sorgu5,(new_wrongpassnumber,userid))
               mysql.connection.commit()

               session["logged_in"] = True
               session["username"] = username

               return redirect(url_for("index"))
           else:
               userid = data["id"]
               son_hata = data["wrongpasstime"]
               bugun = datetime.datetime.now() 
               fark = bugun - son_hata
               if fark <= timedelta (minutes = 45):
                    new_wrongpassnumber = data["wrongpassnumber"] + 1
               elif fark > timedelta (minutes = 45):  
                    new_wrongpassnumber = 1   
               else:
                    new_wrongpassnumber = data["wrongpassnumber"]
               sorgu1 = "Update users Set wrongpasstime = %s where id = %s "
               sorgu2 = "Update users Set wrongpassnumber = %s where id = %s "
               cursor = mysql.connection.cursor()
               cursor.execute(sorgu1,(bugun,userid))
               cursor.execute(sorgu2,(new_wrongpassnumber,userid))
               if new_wrongpassnumber == 3:
                   sorgu4 = "Update users Set status = 'inactive' where id = %s "
                   cursor.execute(sorgu4,(userid,))
                   flash("Üye inaktif edildi","success")
               mysql.connection.commit()
               flash("Parolanızı Yanlış Girdinizz.","danger")
               return redirect(url_for("login")) 

       else:
           flash("Böyle bir kullanıcı bulunmuyor.","danger")
           return redirect(url_for("login"))

    
    return render_template("login.html",form = form)

# Logout İşlemi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Kontrol Paneli Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From users"

    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")

# Makale Ekleme
@app.route("/addarticle", methods = ["GET","POST"])
def addarticle():
    form = ArticleForm(request.form) # addarticle.html sayfasında göstermek için eklemek gerekli.
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()

        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"

        cursor.execute(sorgu,(title,session["username"],content))

        mysql.connection.commit()

        cursor.close()

        flash("Makale Başarıyla Eklendi","success")

        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form = form) # form = form demek formu addarticle.html sayfasında göstermek için gerekli.

# Makale Formu
class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.Length(min = 5,max = 100)]) 
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min = 10)])

# Makale Sayfası
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles"

    result = cursor.execute(sorgu)

    if result > 0: # Database'de makale varsa
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

# Makale Detay Sayfası
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    
    sorgu = "Select * from articles where id = %s"

    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        # makale article.html'e gönderiliyor.
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")

# Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    result = 1
    # Kendimize ait makalemiz varsa aşağıdaki if bloğu çalışacak.
    if result > 0:
        sorgu2 = "Delete from users where id = %s"

        cursor.execute(sorgu2,(id,))

        mysql.connection.commit()
        flash("Üye silindi","success")
        return redirect(url_for("dashboard"))
        flash("Üye silindi","success")
        
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
        return redirect(url_for("index"))

# Makale Güncelleme
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):
    cursor = mysql.connection.cursor()

    # cursor.execute("Select * From users where id = %s") 
    sorgu = "Select * From users where id = %s"
    cursor.execute(sorgu,(id,))
    
    # thisdict["brand"]
    data = cursor.fetchone()

    if data["status"] == "inactive":
        sorgu1 = "Update users Set status = 'active' where id = %s "
        cursor.execute(sorgu1,(id,))
        flash("Üye aktif edildi","success")
    else:
        sorgu2 = "Update users Set status = 'inactive' where id = %s "
        cursor.execute(sorgu2,(id,))
        flash("Üye inaktif edildi","success")

    mysql.connection.commit()

    

    return redirect(url_for("dashboard"))

# Arama 
@app.route("/search",methods = ["GET","POST"])
def search():
    # Direk /search url girildiğinde otomatik olarak anasayfaya gitmesi lazım. Get request koşulunda yani.
   if request.method == "GET":
       return redirect(url_for("index"))
   else:
       # Posttan gelen değeri almak için, request içinde form diye değişken var, bunun içindeki keyword'ü get ile almak için.
       keyword = request.form.get("keyword")

       cursor = mysql.connection.cursor()

       sorgu = "Select * from articles where title like '%" + keyword +"%'"

       result = cursor.execute(sorgu)

       if result == 0:
           flash("Aranan kelimeye uygun makale bulunamadı...","warning")
           return redirect(url_for("articles"))
       else:
           articles = cursor.fetchall()
            # Bulunan makaleleri articles.html sayfasına gönderiyoruz.
           return render_template("articles.html",articles = articles)

if __name__ == "__main__":
    # Hata mesajlarını görebilmemiz için debug true parametre verdik.
    app.run(debug=True)
