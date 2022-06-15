from flask import Flask,redirect,url_for,render_template,request,Response
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from fbprophet import Prophet
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
import json
import os 

import plotly.express as px
import matplotlib.pyplot as plt
plt.style.use('fivethirtyeight')
#from prophet import Prophet

app=Flask(__name__)
db=SQLAlchemy(app)
bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] ='postgresql://virifootynkawq:9527c9522ba230bd8b032c08938849efcc11be8390bdfd12b0192f3785b9ac29@ec2-52-71-23-11.compute-1.amazonaws.com:5432/dc416806kv7niu'
app.config['SECRET_KEY'] ='sk'


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
def check_df(data):
    if len(data.columns)>2 : 
        return False
    elif data.columns[0]!="ds" or data.columns[1]!="y":
        return False     
    else :
        return True    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)




def check_username(username):
        existing_user_username = User.query.filter_by(
            username=username).first()
        return existing_user_username
def get_freq(data): 
    
    data[data.columns[0]]= pd.DataFrame(data[data.columns[0]],dtype='datetime64[ns]')
    start=data.iloc[0,0]
    end =data.iloc[1,0]
    diff= (end-start).days 
    print("diff",diff)
    if diff==1 : 
        return("D")
    elif diff<32 : 
        return("M")
    elif diff>363 :
        return("Y")     

@app.route("/register", methods=['GET', 'POST'])
def register():
    check=False
    if request.method == "POST":
     username=request.form.get('username')
     pwd=request.form.get('pwd')
     check=check_username(username)
     if check : 
        return render_template('register.html',erreur=check)
     else : 
      hashed_password = bcrypt.generate_password_hash(pwd).decode('utf-8')
      new_user = User(username=username, password=hashed_password)
      db.session.add(new_user)
      db.session.commit()
      return render_template('login.html',reussi=True)

    return render_template('register.html',erreur=check)
@app.route("/",methods=['GET', 'POST'])
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
     username=request.form.get('username')
     pwd=request.form.get('pwd')
     user = User.query.filter_by(username=username).first()
     if user:
            if bcrypt.check_password_hash(user.password, pwd):
                login_user(user)
                return redirect(url_for('home'))
     else : 
        render_template("login.html",erreur=True)      
    return render_template("login.html")
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/home")
@login_required
def home():
    
    return render_template("index.html") 

@app.route("/forcast", methods=['GET', 'POST'])
@login_required

def forcast():
    if request.method=="POST":
          script_dir = os.path.dirname(__file__)
          
          f = request.files['data']
          f.save(f.filename)
          
          df=pd.read_csv(f.filename)
          chosen_file=f.filename
          if len(df.columns)==2 : 
           col1=df.columns[0]
           col2=df.columns[1]
           df.rename(columns={col1:"ds",col2:"y"},inplace=True)         
            #Get data periodality 
  
          
           x=json.dumps(df["ds"].to_json())
           y=json.dumps(df["y"].to_json())
           rdct = { "res": "false"}
           res=json.dumps(rdct)
           freq=get_freq(df)

           return   render_template('data.html',filename=chosen_file,x=x,y=y,pl=True,res=res,freq=freq)
          else : 
            return render_template("forcast.html",erreur="Check your csv file columns") 
           # m.fit(df)
          
            # forcast : 
            #future = m.make_future_dataframe(periods=365)
            #future.tail()
             
    else : 
        return render_template("forcast.html")   


@app.route("/forcast/data",methods=['GET', 'POST'])
@login_required

def data():
    
     if request.method=="POST":
        
          f=request.form.get("step")
          seas=request.form.get("seas")
          period=request.form.get("period")
          growth=request.form.get("d")
          df=pd.read_csv(f)
          minimum=request.form.get("min")
          maximum=request.form.get("max")

          m=Prophet(growth=growth)
          col1=df.columns[0]
          col2=df.columns[1]
          df.rename(columns={col1:"ds",col2:"y"},inplace=True)
          if growth=="logistic" : 
            df["cap"]=float(maximum)
            df["floor"]=float(minimum)
          m.fit(df)
          future = m.make_future_dataframe(periods=int(period),freq = get_freq(df))
          if growth=="logistic" : 
            future["cap"]=float(maximum)
            future["floor"]=float(minimum)
          forecast = m.predict(future)
          y_hat = forecast['yhat'].tolist()
          dates = forecast['ds'].apply(lambda x: str(x).split(' ')[0]).tolist()
          new_filename="forecast_results_"+str(f)+".csv"
          forecast.to_csv(new_filename)
          
          #dates=forecast['ds'].to_json()
          y1=json.dumps(y_hat)
          x1=json.dumps(dates)
          x=json.dumps(df["ds"].to_json())
          y=json.dumps(df["y"].to_json())
          
          json.dumps({"res":True})
          return   render_template("result.html",new_filename=new_filename,filename=request.args.get("filename"),pl=request.args.get('pl'),x1=x1,y1=y1,x=x,y=y,res={ "res": "true"}) 

    
     return   render_template("data.html",filename=request.args.get("filename"),x=request.args.get('x'),y=request.args.get('y'),pl=request.args.get('pl'),res={ "res": "false"},freq=request.args.get("freq")) 

@app.route('/forcast/data/result',methods=['GET', 'POST'])
@login_required

def result():
    return  render_template("result.html") 

@app.route('/about')

@login_required
def about():
    return render_template("about.html")   
@app.route("/get_csv/<filename>")
def get_csv(filename):
    csv = filename
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=forcasting_results.csv"})

if __name__=="__main__" : 
    app.run()
