import os
import secrets
import smtplib
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from sdwan import app, db, bcrypt, mail
from sdwan.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                         PostForm, RequestResetForm, ResetPasswordForm ,
                         CreateOrganizationForm,DeleteOrganizationForm,
                         CreateTemplateForm,DeleteTemplateForm,CreateNetworkForm)
from sdwan.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
import meraki
from meraki.exceptions import APIError
API_KEY = "9b6b5466f2f02d83c992e865518ea3753594f374"

dashboard = meraki.DashboardAPI(api_key=API_KEY,suppress_logging=True)

@app.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('index.html', posts=posts)

@app.route("/")
@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)


def send_reset_email(user):
    token = user.get_reset_token()
    with smtplib.SMTP("smtp.mail.yahoo.com") as connection:
        my_email = "pinkytonny@yahoo.com"
        password = "glvrafsdohlvhugp"
        # my_email = "lakshmikn7387@gmail.com"
        # password = "Ashakn@123"

        connection.starttls()
        connection.login(user=my_email, password=password)
        connection.sendmail(
            from_addr=my_email,
            to_addrs=[user.email],
            msg=f'''Subject:'Password Reset Request'\n\n To reset your password, visit the following link:
             {url_for('reset_token', token=token, _external=True)}
             If you did not make this request then simply ignore this email and no changes will be made.
             ''')
        connection.close()


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@app.route("/Meraki")
def Meraki():
    return render_template("Meraki.html",title='Meraki')

@app.route("/Velocloud")
def Velocloud():
    return render_template("Velocloud.html",title='Velocloud')

@app.route("/Meraki/getOrganizations")
def getOrganizations():
    Organization_list = dashboard.organizations.getOrganizations()
    return render_template("getOrganizations.html",Org_list=Organization_list)


@app.route("/Meraki/CreateOrganization",methods=['GET', 'POST'])
def CreateOrganization():
    form = CreateOrganizationForm()
    if form.validate_on_submit():
        dashboard.organizations.createOrganization(name=form.NewOrganization.data)
        flash(f'{form.NewOrganization.data} Organization got created', 'success')
    return render_template("CreateOrganization.html",form=form)


@app.route("/Meraki/DeleteOrganization",methods=['GET', 'POST'])
def DeleteOrganization():
    form = DeleteOrganizationForm()
    if form.validate_on_submit():
        Organization_list = dashboard.organizations.getOrganizations()
        Organization_Name = []
        for i in Organization_list:
            Organization_Name.append(i["name"])

        def match_organizationname(org_name):
            for i in Organization_list:
                if i["name"] == org_name:
                    org_id = i["id"]
                    return org_id

        if form.DeleteOrganization.data not in Organization_Name:
            flash(f"{form.DeleteOrganization.data} not present in Organization List","danger")
        else:
            dashboard.organizations.deleteOrganization(match_organizationname(form.DeleteOrganization.data))
            flash(f"{form.DeleteOrganization.data} Organization got deleted","success")
    return render_template("DeleteOrganization.html",form=form)


@app.route("/Meraki/CreateTemplate",methods=['GET', 'POST'])
def CreateTemplate():
    form = CreateTemplateForm()
    if form.validate_on_submit():
        Organization_list = dashboard.organizations.getOrganizations()
        Organization_Name = []
        for i in Organization_list:
            Organization_Name.append(i["name"])

        print(Organization_Name)
        def match_organizationname(org_name):
            for i in Organization_list:
                if i["name"] == org_name:
                    org_id = i["id"]
                    return org_id

        if form.OrganizationName.data not in Organization_Name:
            print("entered")
            flash(f"{form.OrganizationName.data} not present in Organization List", "danger")
        else:
            dashboard.organizations.createOrganizationConfigTemplate(organizationId=match_organizationname(form.OrganizationName.data),name=form.TemplateName.data)
            flash(f"{form.TemplateName.data} Template got created","success")

    return render_template("CreateTemplate.html",form=form)


@app.route("/Meraki/DeleteTemplate",methods=['GET', 'POST'])
def DeleteTemplate():
    form = DeleteTemplateForm()
    if form.validate_on_submit():
        Organization_list = dashboard.organizations.getOrganizations()
        Organization_Name = []
        print(Organization_Name)

        for i in Organization_list:
            Organization_Name.append(i["name"])

        def match_organizationname(org_name):
            for i in Organization_list:
                if i["name"] == org_name:
                    org_id = i["id"]
                    return org_id

        if form.OrganizationName.data not in Organization_Name:
            flash(f"{form.OrganizationName.data} not present in Organization List", "danger")
        else:
            template_list = dashboard.organizations.getOrganizationConfigTemplates(
                organizationId=match_organizationname(form.OrganizationName.data))
            template_name = []
            for i in template_list:
                template_name.append(i["name"])

            def templatematch(templatename):
                for i in template_list:
                    if i["name"] == templatename:
                        template_id = i["id"]
                        return template_id

            if form.TemplateName.data not in template_name:
                flash(f'{form.TemplateName.data} template not found in {form.OrganizationName.data} Organization',"danger")
            else:
                dashboard.organizations.deleteOrganizationConfigTemplate(
                    organizationId=match_organizationname(form.OrganizationName.data),
                    configTemplateId=templatematch(form.TemplateName.data))
                flash(f"{form.TemplateName.data} Template got deleted", "success")

    return render_template("DeleteTemplate.html", form=form)


@app.route("/Meraki/ListNetworks",methods=['GET', 'POST'])
def ListNetworks():
    form = CreateOrganizationForm()
    if form.validate_on_submit():
        Organization_list = dashboard.organizations.getOrganizations()
        Organization_Name = []
        print(Organization_Name)

        for i in Organization_list:
            Organization_Name.append(i["name"])

        def match_organizationname(org_name):
            for i in Organization_list:
                if i["name"] == org_name:
                    org_id = i["id"]
                    return org_id

        if form.NewOrganization.data not in Organization_Name:
            flash(f"{form.NewOrganization.data} not present in Organization List", "danger")
        else:
            Network_list = dashboard.organizations.getOrganizationNetworks(organizationId=match_organizationname(form.NewOrganization.data))
            return render_template("getNetworks.html",networklist=Network_list,Organizationname=form.NewOrganization.data)

    return render_template("CreateOrganization.html",form=form)


@app.route("/Meraki/CreateNetwork",methods=['GET', 'POST'])
def CreateNetwork():
    form = CreateNetworkForm()
    if form.validate_on_submit():
        Organization_list = dashboard.organizations.getOrganizations()
        Organization_Name = []
        print(Organization_Name)

        for i in Organization_list:
            Organization_Name.append(i["name"])

        def match_organizationname(org_name):
            for i in Organization_list:
                if i["name"] == org_name:
                    org_id = i["id"]
                    return org_id

        if form.OrganizationName.data not in Organization_Name:
            flash(f"{form.OrganizationName.data} not present in Organization List", "danger")
        else:
            if form.MinRange.data > form.MaxRange.data:
                flash(f"\nMinRange should be lesser than MaxRange\n","danger")
            else:
                for i in range(form.MinRange.data, form.MaxRange.data + 1):
                    try:
                        dashboard.organizations.createOrganizationNetwork(organizationId=match_organizationname(form.OrganizationName.data),
                                                                          name=f"{form.NetworkName.data}{i}",
                                                                          productTypes=["Appliance"])
                        flash(f"\n{form.NetworkName.data}{i} Network has created inside {form.OrganizationName.data} Organization\n","success")

                    except meraki.exceptions.APIError:
                        flash(f"{form.NetworkName.data}{i} is already present in organization","danger")

    return render_template('CreateNetwork.html',form=form)


@app.route("/Meraki/DeleteNetwork",methods=['GET', 'POST'])
def DeleteNetwork():
    form = CreateNetworkForm()
    if form.validate_on_submit():

        Organization_list = dashboard.organizations.getOrganizations()
        Organization_Name = []
        print(Organization_Name)

        for i in Organization_list:
            Organization_Name.append(i["name"])

        def match_organizationname(org_name):
            for i in Organization_list:
                if i["name"] == org_name:
                    org_id = i["id"]
                    return org_id

        if form.OrganizationName.data not in Organization_Name:
            flash(f"{form.OrganizationName.data} not present in Organization List", "danger")
        else:
            def match_networks(network_name, org_id):
                network_list = dashboard.organizations.getOrganizationNetworks(organizationId=org_id)
                for i in network_list:
                    if i["name"] == network_name:
                        network_id = i["id"]
                        return network_id

            if form.MinRange.data > form.MaxRange.data:
                flash(f"\nMinRange should be lesser than MaxRange\n","danger")
            else:
                for i in range(form.MinRange.data, form.MaxRange.data + 1):
                    try:
                        dashboard.networks.deleteNetwork(networkId=match_networks(f"{form.NetworkName.data}{i}",match_organizationname(form.OrganizationName.data)))
                        flash(f"\n{form.NetworkName.data}{i} Network deleted from {form.OrganizationName.data} Organization\n","success")

                    except meraki.exceptions.APIError:
                        flash(f"{form.NetworkName.data}{i} is not present in {form.OrganizationName.data}organization","danger")

    return render_template('CreateNetwork.html',form=form)


def claim_device():
    print("Organization List :\n")
    list_organizations()
    organization_name = input("Enter Organization Name of Network where device needs to be claimed:\n")
    list_networks(organization_name)

    network_name = input("Select Network from above List :\n")
    serialnumber = input("Provide Serial number of device :\n")
    dashboard.networks.claimNetworkDevices(networkId=match_networks(network_name,match_organizationname(organization_name)), serials=[serialnumber])
    print(f"{serialnumber} serial number device added to {network_name} Network")


def delete_device():
headers = {
'X-Cisco-Meraki-API-Key': API_KEY,
'Content-Type': 'application/json'
}

print("Organization List :\n")
list_organizations()

organization_name = input("Enter Organization Name of Network from where device needs to be deleted.")
network_list = list_networks(organization_name)

if network_list == []:
print(f"\nWARNING: There are no networks present in {organization_name} Organization..so there will be no device connected to network")
else:

network_name = input("Select Network from above List :\n")

network_id = match_networks(network_name,match_organizationname(organization_name))
print(f"\n List of Serial Numbers Present in {network_name} Network :\n")
device_list = dashboard.networks.getNetworkDevices(networkId=network_id)
for i in device_list:
    print(f'{i["serial"]} connected to {network_name} Network')

if device_list == []:
    print(f"\n WARNING: {network_name} Network has no Network Devices to Delete")

else:
    serialnumber = input("\nProvide Serial number of device from above List:\n")

    url = f"https://api.meraki.com/api/v0/networks/{network_id}/devices/{serialnumber}/remove"

    # Send request and get response
    response = requests.post(
        url,
        headers=headers,
        verify=False
    )

    print(response)
    print(f"{serialnumber} serial number device has deleted from  {network_name} Network")