import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask,redirect,render_template,request, url_for, flash,session
from flask_bootstrap import Bootstrap
from datetime import datetime
from flask_login import login_required,current_user,LoginManager,UserMixin,login_user, logout_user
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField,SubmitField,PasswordField,BooleanField
from wtforms.validators import DataRequired
from sqlalchemy import extract,and_

app = Flask(__name__)
bootstrap = Bootstrap(app)
app.config['SQLALCHEMY_DATABASE_URI']='postgresql://school:school@localhost:5432/schoolwork'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SECRET_KEY"] = 'XHmi8uLWRbyVr3au2v92dXZW1'
app.config.from_object(__name__)
db=SQLAlchemy(app)
moment = Moment(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'#路由为login


class User(UserMixin,db.Model):
	__tablename__='user'
	id=db.Column(db.Integer,primary_key=True,index=True)
	name=db.Column(db.String(64),unique=True)
	email=db.Column(db.String(64),unique=True)
	password=db.Column(db.String(256))
	sex=db.Column(db.String(16))
	birthday=db.Column(db.String(64))
	education=db.Column(db.String(16))
	address=db.Column(db.String(128))
	telephone=db.Column(db.String(64))
	workage=db.Column(db.Integer)
	salary=db.Column(db.Integer)
	role_id = db.Column(db.Integer,default=0)

#role_id =1 :超级用户，0为普通工程师
class Posts(db.Model):
	__tablename__='posts'
	id=db.Column(db.Integer,primary_key=True)
	pclass = db.Column(db.Text)
	body=db.Column(db.Text)
	timestamp = db.Column(db.DateTime,index=True,default=datetime.utcnow)
	kptime=db.Column(db.Integer)
	people_id=db.Column(db.Integer)
	allowd=db.Column(db.Integer,default=0)#=0表示还没通过审核

class Salary(db.Model):#如果要对people_id和time建立联合唯一约束，建议pgadmin添加，然后管理员提交前进行判断
	__tablename__='salarys'
	id=db.Column(db.Integer,primary_key=True)
	people_id=db.Column(db.Integer)
	time=db.Column(db.String(64))#必须是字符串格式，格式为年/月，自动输入
	salary=db.Column(db.Integer)

def salary_stat(uid,ddt):#传入员工id和年月日期，统计当月薪酬（按照当前工资来算），月份是str格式
	strdt=datetime.strptime(ddt, "%Y-%m").strftime("%Y-%m")
	print('strdt='+strdt)
	uyear=int(strdt.split('-')[0])
	umonth=int(strdt.split('-')[1])
	print(str(uyear),str(umonth))
	events= Posts.query.filter(and_(extract('year', Posts.timestamp) == uyear,extract('month', Posts.timestamp) == umonth,Posts.people_id == uid)).all()#获取所有满足条件的事件
	print(len(events))
	#计算公式:每月工作160小时算，薪酬=(基本薪酬/160)*(160-2*请假小时数-4*缺勤小时数+3*加班小时数)取整
	actual_hours = 0
	b_sa=User.query.filter_by(id=uid).first().salary
	for ipost in events:
		if ipost.pclass=='请假':
			actual_hours-=2*ipost.kptime
		elif ipost.pclass=='缺勤':
			actual_hours-=4*ipost.kptime
		elif ipost.pclass=='迟到':
			actual_hours-=4*ipost.kptime
		elif ipost.pclass=='加班':
			actual_hours+=3*ipost.kptime
	return int((b_sa/160)*(160+actual_hours))

@login_manager.user_loader
def load_user(user_id):#加载已经登录用户的信息
	return User.query.get(int(user_id))

class LoginForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住登录状态')
    submit = SubmitField('登入')

@app.route('/login', methods=['GET', 'POST'])#登录界面√，相当于首页了
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.password==form.password.data:#要改验证函数（验证是否和表单密码相同）
            login_user(user, form.remember_me.data)
            return redirect(url_for('index'))
        flash('无效的用户名或者密码')
    return render_template('login.html', form=form)#无论何时都返回这个表单，只要后面根据登录状态决定是否渲染即可

@app.route('/logout')#登出逻辑√
@login_required
def logout():
	logout_user()
	flash('你已经登出')
	return redirect(url_for('index'))

def read_name():
	rtl=[]
	general_role=User.query.filter_by(role_id=0).all()
	for u in general_role:
		rtl.append(u.name)
	return rtl

#下拉框表单：
class WatchForm(FlaskForm):
    tags = SelectField(label='用户名', choices=read_name(),validators=[DataRequired()])
    submit = SubmitField(label='提交')


@app.route('/',methods=['GET','POST'])#个人资料界面，也要登录
@login_required
def index():
	#渲染的部分直接在html中完成，除非是管理员用户
	if not current_user:
		return render_template('user.html')
	if current_user.role_id==1:
		form = WatchForm()
#备注一下获取表单动态修改：用dir(对象)获取属性列表，form.tags.kwargs['choices']=['new']可以修改choices属性，以此类推
		#返回选定用户的信息，看request的参数，且必须返回一个下拉框列表表单数据（用户列表）
		if form.validate_on_submit():
			user = User.query.filter_by(name=form.tags.data).first()
			session['dstuser']=form.tags.data
			flash('已更新显示信息')
			return render_template('user.html',form=form,user=user)
		elif 'dstuser' in session.keys():
			user = User.query.filter_by(name=session['dstuser']).first()
			return render_template('user.html',form=form,user=user)
		else:
			return render_template('user.html',form=form,user=current_user)
	else:#返回current_user的信息,这些信息由模板主动提取，确定一下current_user能不能自动返回，不然还要在函数里返回有点麻烦
		return render_template('user.html')

@app.route('/posts',methods=['GET','POST'])#事件界面
@login_required
def posts_dis():#传递事件列表，这个是个人的，根据用户id筛选，且只返回审批过的
	if not current_user:
		flash('检测不到登录！')
		return render_template('user.html')
	if current_user.role_id!=1:
		page=request.args.get('page',1,type=int)
		pagination=Posts.query.filter_by(people_id=current_user.id,allowd=1).order_by(Posts.timestamp.desc()).paginate(page,per_page=20,error_out=False)
		posts=pagination.items
	#post选择出people_id=此用户的（如果是管理员，则是传入另一个参数）
		return render_template('list.html',pagination=pagination,posts=posts)
	else:
		form = WatchForm()
		page=request.args.get('page',1,type=int)
		if form.validate_on_submit():
			nuid= User.query.filter_by(name=form.tags.data).first().id
		else:
			nuid = User.query.filter_by(role_id=1).first().id
		pagination=Posts.query.filter_by(people_id=nuid,allowd=1).order_by(Posts.timestamp.desc()).paginate(page,per_page=20,error_out=False)
		posts=pagination.items
		return render_template('list.html',pagination=pagination,posts=posts,form=form)

#这里还需要统计操作的按钮，用<input type="submit" name="submit_button" value="THING1"><br>    if request.method == 'POST':if request.form['submit_button'] == 'THING1':来处理信息

#写入事件post:写入一个post，写入以后重定向到同一个页面,目前还没有写表单
#事件post表单：
class WpostForm(FlaskForm):
    pclass = SelectField(label='事件类型', choices=['请假'],validators=[DataRequired()])
    body = StringField('描述',validators=[DataRequired()])
    kptime = StringField('持续时间/小时数',validators=[DataRequired(),])#验证函数用数字
    submit = SubmitField(label='提交')

@app.route('/w_post', methods=['get','post'])#这个页面不对管理员开放，但可以由api提交迟到事件
@login_required
def w_post():#提交表单的页面，提交成功后给出闪现消息
	form = WpostForm()
	if form.validate_on_submit():
		try:
			global db#要修改时需要声明全局
			new_post = Posts(pclass=form.pclass.data,body=form.body.data,kptime=form.kptime.data,people_id=current_user.id)#这里得改一下表单用法
			db.session.add(new_post)
			db.session.commit()
			flash('已成功提交事件')
		except:
			flash('提交事件失败')
	return render_template('w_post.html',form=form)

@app.route('/api_post')
def api_post():
	if request.args.get("key")!='thisisakeyexample':
		return('Key error!')
	else:
		try:
			global db
			new_post = Posts(pclass=request.args.get("c"),body=request.args.get("b"),kptime=request.args.get("kt"),people_id=request.args.get("uid"))
			db.session.add(new_post)
			db.session.commit()
			return('Commited')
		except:
			return('Commit error!')

@app.route('/api_app')
@login_required
def api_app():#审核api，传入一个pid参数和一个allow参数
	global db
	if current_user.role_id!=1:
		return('Permission denied')
	post_id=int(request.args.get("pid"))
	cpost=Posts.query.filter_by(id=post_id).first()
	if int(request.args.get("allow"))==1:
		cpost.allowd=1
	else:
		db.session.delete(cpost)
	db.session.commit()
	flash('已经更新事件列表')
	return redirect(url_for('approval'),code=302)

@app.route('/approval')
@login_required
def approval():#审核页面，和list区别是获取的数据不按人分，按是否被允许分
	global db
	if not current_user:
		flash('检测不到登录！')
		return render_template('user.html')
	if current_user.role_id!=1:
		flash('非管理员没有权限操作')
		return render_template('user.html')
	else:
		page=request.args.get('page',1,type=int)
		pagination=Posts.query.filter_by(allowd=0).order_by(Posts.timestamp.desc()).paginate(page,per_page=20,error_out=False)
		posts=pagination.items
		return render_template('approval.html',pagination=pagination,posts=posts)

@app.route('/sast_api')
@login_required
def sast_api():
	duid=int(request.args.get("pid"))
	if request.args.get('strdate'):
		dstdt=request.args.get('strdate')
	else:
		dstdt=datetime.now().strftime("%Y-%m")
	print('dstdt='+dstdt)
	dsalary=str(salary_stat(duid,dstdt))
	dun=User.query.filter_by(id=duid).first().name
	flash_str=dun+'的当月薪酬是'+dsalary
	flash(flash_str)
	return redirect(url_for('index'),code=302)

@app.route('/sast_total')
@login_required
def sast_total():
	if request.args.get('strdate'):
		dstdt=request.args.get('strdate')
	else:
		dstdt=datetime.now().strftime("%Y-%m")
	print('dstdt='+dstdt)
	sa_list=User.query.filter_by(role_id=0).all()
	dsalary=0
	for duid in sa_list:
		print('uid=',duid.id)
		dsalary+=salary_stat(int(duid.id),dstdt)
	flash_str='部门本月薪酬总计是'+str(dsalary)
	flash(flash_str)
	return redirect(url_for('index'),code=302)

@app.route('/tes')
def tes_ret():
	flash('Test!')
	return render_template('test.html')

app.run()