from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField,TextAreaField,IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError,Optional
from sdwan.models import User


class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')


class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Post')


class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. You must register first.')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class CreateOrganizationForm(FlaskForm):
    NewOrganization = StringField('Enter Organization Name',
                           validators=[DataRequired(), Length(min=2, max=20)])
    submit = SubmitField('Submit')


class DeleteOrganizationForm(FlaskForm):
    DeleteOrganization = StringField('Enter Oganization Name which needs to be deleted',
                           validators=[DataRequired(), Length(min=2, max=20)])
    submit = SubmitField('DeleteOrganization')


class CreateTemplateForm(FlaskForm):
    OrganizationName = StringField('Enter Organization Name',validators=[DataRequired(), Length(min=2, max=20)])
    TemplateName = StringField('Enter Template Name',validators=[DataRequired(), Length(min=2, max=20)])
    submit = SubmitField('Create Template')


class DeleteTemplateForm(FlaskForm):
    OrganizationName = StringField('Enter Organization Name', validators=[DataRequired(), Length(min=2, max=20)])
    TemplateName = StringField('Enter Template Name', validators=[DataRequired(), Length(min=2, max=20)])
    submit = SubmitField('Delete Template')


class CreateNetworkForm(FlaskForm):
    OrganizationName = StringField('Enter Organization Name', validators=[DataRequired(), Length(min=2, max=20)])
    NetworkName = StringField('Enter Network Name', validators=[DataRequired(), Length(min=2, max=20)])
    MinRange = IntegerField('Enter Min Range Value', validators=[DataRequired()])
    MaxRange = IntegerField('Enter Min Range Value', validators=[DataRequired()])
    submit = SubmitField('Submit')
