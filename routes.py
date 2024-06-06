import os
from werkzeug.utils import secure_filename
from flask_apscheduler import APScheduler
from flask import Flask, render_template, request, redirect, url_for, session, flash, Blueprint, jsonify, Response
import sqlite3
import hashlib
import cv2
import dlib
import numpy as np
import uuid
from datetime import datetime, timedelta
import random
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

routes_bp = Blueprint('routes', __name__, url_prefix='')

@routes_bp.route('/')
def index():
    return render_template('login.html')

UPLOAD_FOLDER = 'static/ProfilePictures'
DATABASE_FOLDER = 'database'


#################################### Fuction to save profile pictures Start ####################################

def save_profile_picture(file, user_role, fname, lname, userid):
    subfolder = 'Faculty' if user_role == 'faculty' else 'Student'
    folder_path = os.path.join(UPLOAD_FOLDER, subfolder)
    os.makedirs(folder_path, exist_ok=True)
    
    ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    filename = f"{fname}_{lname}_{userid}.{ext}"
    file_path = os.path.join(folder_path, filename)
    
    file.save(file_path)
    return file_path

#################################### Fuction to save profile pictures End ####################################

#################################### Route for Team Page Start  ####################################

@routes_bp.route('/team')
def team():
    return render_template('team.html')

#################################### Route for Team Page Start  ####################################


#################################### Route for Student Signup Start ####################################

@routes_bp.route('/studentsignup', methods=['GET', 'POST'])
def studentsignup():
    if request.method == 'POST':
        userid = request.form['userid']
        if is_userid_existing(userid):
            flash('User ID already exists. Please choose another.', 'error')
            return redirect(url_for('.studentsignup'))
        
        fname = request.form['fname']
        lname = request.form.get('lname')  
        dob = request.form.get('dob')  
        collegename = request.form['collegename']
        departmentname = request.form['departmentname']
        semester = request.form['semester']
        section = request.form['section']
        profile_picture = request.files['profilepicture']
        profile_picture_path = save_profile_picture(profile_picture, 'student', fname, lname, userid)
        password = request.form['password']
        email = request.form['email']
        phonenumber = request.form['phonenumber']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        start_year = int(request.form['startYear'])
        end_year = int(request.form['endYear'])
        LEET = request.form['leetStudent']
        
        if LEET == 'yes':
            start_year -= 1
        
        batch = f"{start_year}-{end_year}"
        
        db_path = os.path.join(DATABASE_FOLDER, 'Students.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute('''
                  CREATE TABLE IF NOT EXISTS users (
                      id INTEGER PRIMARY KEY,
                      userid INTEGER NOT NULL,
                      fname TEXT NOT NULL,
                      lname TEXT,
                      dob TEXT,
                      collegename TEXT,
                      departmentname TEXT,
                      semester TEXT,  
                      section TEXT,    
                      profile_picture TEXT,
                      password TEXT NOT NULL,
                      role TEXT DEFAULT 'student',  
                      verified TEXT DEFAULT 'pending',
                      email TEXT,
                      phonenumber INTEGER,
                      batch TEXT,
                      LEET TEXT
                  )
                  ''')
        
        c.execute("INSERT INTO users (userid, fname, lname, dob, collegename, departmentname, semester, section, profile_picture, password, role, email, phonenumber, batch, LEET) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
          (userid, fname, lname, dob, collegename, departmentname, semester, section, profile_picture_path, hashed_password, 'student', email, phonenumber, batch, LEET))
        
        conn.commit()
        conn.close()
        
        flash('You have successfully signed up!', 'success')
        return redirect(url_for('.studentdashboard'))
    
    return render_template('studentsignup.html')

#################################### Route for Student Signup End ####################################


#################################### Route for Student Verification Start ####################################

@routes_bp.route('/set_profile_status', methods=['POST'])
def set_profile_status():
    try:
        data = request.json
        userid = data.get('userId')
        status = data.get('status')
        semester = data.get('semester')
        section = data.get('section')

        conn = sqlite3.connect('database/Students.db')
        cursor = conn.cursor()

        cursor.execute("UPDATE users SET verified = ? WHERE userid = ? AND semester = ? AND section = ?", (status, userid, semester, section))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'message': f"Status updated to {status} for user ID {userid}"}), 200

    except Exception as e:
        error_message = f"Error setting verification status: {str(e)}"
        print(error_message)
        return jsonify({'error': error_message}), 500




#################################### Route for Student Verification Start ####################################

#################################### Route to check whether the userid exists or not Start ####################################

@routes_bp.route('/check_userid', methods=['POST'])
def check_userid():
    userid = request.form['userid']
    if is_userid_existing(userid):
        return jsonify({'exists': True})
    else:
        return jsonify({'exists': False})

def is_userid_existing(userid):
    student_db_path = os.path.join(DATABASE_FOLDER, 'Students.db')
    conn_student = sqlite3.connect(student_db_path)
    c_student = conn_student.cursor()
    c_student.execute("SELECT userid FROM users WHERE userid=?", (userid,))
    existing_userid_student = c_student.fetchone()
    conn_student.close()
    
    faculty_db_path = os.path.join(DATABASE_FOLDER, 'FacultyMember.db')
    conn_faculty = sqlite3.connect(faculty_db_path)
    c_faculty = conn_faculty.cursor()
    c_faculty.execute("SELECT userid FROM users WHERE userid=?", (userid,))
    existing_userid_faculty = c_faculty.fetchone()
    conn_faculty.close()
    
    return existing_userid_student is not None or existing_userid_faculty is not None

#################################### Route to check whether the userid exists or not End ####################################


#################################### Route to check whether the userid present or not Start ####################################

@routes_bp.route('/userid_present', methods=['GET'])
def userid_present():
    role = request.args.get('role')
    userid = request.args.get('userid')
    
    if role == 'Student':
        db_path = os.path.join(DATABASE_FOLDER, 'Students.db')
    elif role == 'Faculty':
        db_path = os.path.join(DATABASE_FOLDER, 'FacultyMember.db')
    else:
        return jsonify({'exists': False}), 400
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE userid=?", (userid,))
    user_exists = c.fetchone() is not None
    conn.close()
    
    return jsonify({'exists': user_exists})

#################################### Route to check whether the userid present or not End ####################################


#################################### Route to check whether the phone number exists or not Start ####################################

@routes_bp.route('/check_phonenumber', methods=['POST'])
def check_phonenumber():
    phonenumber = request.form['phonenumber']
    if is_phonenumber_existing(phonenumber):
        return jsonify({'exists': True})
    else:
        return jsonify({'exists': False})

def is_phonenumber_existing(phonenumber):
    student_db_path = os.path.join(DATABASE_FOLDER, 'Students.db')
    conn_student = sqlite3.connect(student_db_path)
    c_student = conn_student.cursor()
    c_student.execute("SELECT phonenumber FROM users WHERE phonenumber=?", (phonenumber,))
    existing_phonenumber = c_student.fetchone()
    conn_student.close()
    
    return existing_phonenumber is not None

#################################### Route to check whether the phone number exists or not End ####################################


#################################### Route for facultysignup Start ####################################

@routes_bp.route('/facultysignup', methods=['GET', 'POST'])
def facultysignup():
    if request.method == 'POST':
        userid = request.form['userid']
        if is_userid_existing(userid):
            flash('User ID already exists. Please choose another.', 'error')
            return redirect(url_for('.facultysignup'))
        fname = request.form['fname']
        lname = request.form.get('lname')  
        dob = request.form.get('dob')  
        collegename = request.form['collegename']
        departmentname = request.form['departmentname']
        role = request.form['role']
        if role == 'Academic Coordinator':
            semesters = request.form.getlist('semesterAC') 
            designation = request.form['InstDesig']  
        elif role == 'TPP Instructor':
            subject = request.form['tpp']                  
        elif role == 'Instructor':
            designation = request.form['InstDesig']      
        elif role == 'Class Counselor':
            designation = request.form['InstDesig']   
        elif role == 'Head of Department':
            designation = request.form['InstDesig']
            
        profile_picture = request.files['profilepicture']
        profile_picture_path = save_profile_picture(profile_picture, 'faculty', fname, lname, userid)
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        db_path = os.path.join(DATABASE_FOLDER, 'FacultyMember.db') 
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                userid TEXT NOT NULL,
                fname TEXT NOT NULL,
                lname TEXT,
                dob TEXT,
                collegename TEXT,
                departmentname TEXT,
                role TEXT,
                semesters TEXT,   -- New column for storing semesters (for Academic Coordinator)
                sections TEXT,    -- New column for storing sections (for Class Counselor)
                subject TEXT,     -- New column for storing subject (for TPP Instructor)
                designation TEXT, -- New column for storing designation (for Instructor)
                profile_picture TEXT,
                password TEXT NOT NULL,
                verified TEXT DEFAULT 'pending'
            )
        ''')
        
        if role == 'Academic Coordinator':
            c.execute("INSERT INTO users (userid, fname, lname, dob, collegename, departmentname, role, semesters, designation, profile_picture, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (userid, fname, lname, dob, collegename, departmentname, role,', '.join(semesters), designation,  profile_picture_path, hashed_password))
        elif role == 'TPP Instructor':
            c.execute("INSERT INTO users (userid, fname, lname, dob, collegename, departmentname, role, subject, profile_picture, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (userid, fname, lname, dob, collegename, departmentname, role, subject, profile_picture_path, hashed_password))
        elif role == 'Instructor':
            c.execute("INSERT INTO users (userid, fname, lname, dob, collegename, departmentname, role, designation, profile_picture, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (userid, fname, lname, dob, collegename, departmentname, role, designation, profile_picture_path, hashed_password))
        elif role == 'Class Counselor':
            c.execute("INSERT INTO users (userid, fname, lname, dob, collegename, departmentname, role, designation, profile_picture, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (userid, fname, lname, dob, collegename, departmentname, role, designation, profile_picture_path, hashed_password))
        else:
            c.execute("INSERT INTO users (userid, fname, lname, dob, collegename, departmentname, role, profile_picture, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (userid, fname, lname, dob, collegename, departmentname, role, profile_picture_path, hashed_password))
        
        conn.commit()
        conn.close()
        
        flash('You have successfully signed up!', 'success')
        return redirect(url_for('.facultydashboard'))
    return render_template('facultysignup.html')

#################################### Route for facultysignup End ####################################


#################################### Function to check is the user is a student Start  ####################################

def is_student(userid):
    db_path = os.path.join(DATABASE_FOLDER, 'Students.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE userid=? AND role='student'", (userid,))
    student = c.fetchone()
    conn.close()
    return student is not None

#################################### Function to check is the user is a student End  ####################################


#################################### Route for user Login Start  ####################################
                
@routes_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']
        role = request.form['role']  
        
        if userid == '1927':
            db_path = os.path.join(DATABASE_FOLDER, 'SuperAdmin.db') 
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE userid=?", (userid,))
            super_admin = c.fetchone()
            conn.close()
            if super_admin and password == super_admin[10]:  
                session['logged_in'] = True
                session['userid'] = userid
                flash('You have successfully logged in as the super admin!', 'success')
                return redirect(url_for('.admin')) 
            else:
                flash('Invalid User ID or Password. Please try again.', 'error')
                return redirect(url_for('.login'))
        else:
            if role == 'Student':
                db_path = os.path.join(DATABASE_FOLDER, 'Students.db')  
                password_index = 10  
                role_index = 11  
            elif role == 'Faculty':
                db_path = os.path.join(DATABASE_FOLDER, 'FacultyMember.db')  
                password_index = 9  
                role_index = 10  
            else:
                flash('Invalid role selected.', 'error')
                return redirect(url_for('.login'))
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE userid=?", (userid,))
            user = c.fetchone()
            conn.close()
            if user:
                hashed_password = user[password_index]  
                hashed_input_password = hashlib.sha256(password.encode()).hexdigest()
                
                if hashed_password == hashed_input_password:
                    if user[role_index] == 'verified':  
                        session['logged_in'] = True
                        session['userid'] = userid
                        
                        session['user_data'] = {
                            'collegename': user[5],
                            'departmentname': user[6],
                            'role': user[7],
                            'section': user[8]
                        }
                        if role == "Student":
                            flash('You have successfully logged in!', 'success')
                            return redirect(url_for('.studentdashboard'))
                        else:
                            flash('You have successfully logged in!', 'success')
                            return redirect(url_for('.facultydashboard'))
                    else:
                        flash('Pending account verification.', 'alert')
                else:
                    flash('Invalid User ID or Password. Please try again.', 'error')
            else:
                flash('User not found.', 'error')
    
    return render_template('login.html')

#################################### Route for user Login End  ####################################


#################################### Route for Logout Start  ####################################

@routes_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    session.pop('userid', None)
    session.pop('user_data', None) 
    flash('You have successfully logged out.', 'success')
    return redirect(url_for('.login'))

#################################### Route for Logout End  ####################################


#################################### Route for admin Start  ####################################

@routes_bp.route('/admin')
def admin():
    if 'logged_in' in session:
        db_path = os.path.join(DATABASE_FOLDER, 'FacultyMember.db') 
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE verified='pending'" )
        pending = c.fetchall()  
        conn.close()
        return render_template('admin.html', pending_users=pending)
    else:
        flash('Please login to access the super admin page.', 'error')
        return redirect(url_for('.login'))
    
#################################### Route for admin End  ####################################


#################################### Route to verify User Start  ####################################    

@routes_bp.route('/verify_user/<user_id>', methods=['POST'])
def verify_user(user_id):
    action = request.form['action']
    
    if action == 'verify':
        db_path = os.path.join(DATABASE_FOLDER, 'FacultyMember.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("UPDATE users SET verified='verified' WHERE userid=?", (user_id,))
        conn.commit()
        conn.close()
        flash(f'User {user_id} verified successfully!', 'Verification')
    elif action == 'not_verify':
        delete_user(user_id)
        flash(f'User {user_id} not verified and removed from the system.', 'info')
    
    return redirect(url_for('.admin'))


def delete_user(user_id):
    db_path = os.path.join(DATABASE_FOLDER, 'FacultyMember.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE userid=?", (user_id,))
    conn.commit()
    conn.close()

#################################### Route to verify User End  #################################### 


#################################### Route for Student Dashboard Start  ####################################

@routes_bp.route('/studentdashboard')
def studentdashboard():
    if 'logged_in' in session:
        userid = session['userid']
        db_file = 'Students.db'
        db_path = os.path.join(DATABASE_FOLDER, db_file)
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT * FROM users WHERE userid=?", (userid,))
        user = c.fetchone()
        conn.close()
        
        if user:
            profile_picture = user[9]
            userid = user[1]
            fname = user[2]  
            lname = user[3]  
            dob = user[4]  
            collegename = user[5]  
            departmentname = user[6]  
            semester = user[7]  
            section = user[8]  
            phonenumber = user[14]
            email = user[13]
            batch = user[15]
            LEET = user[16]

            if user[11] != 'verified':
                flash('Pending account verification.', 'alert')
                return render_template('studentdashboard.html', alert_message='Pending account verification.', profile_picture=profile_picture, userid=userid, fname=fname, lname=lname, dob=dob, collegename=collegename, departmentname=departmentname, semester=semester, section=section, email=email, phonenumber=phonenumber, batch=batch, LEET=LEET)

            return render_template('studentdashboard.html', profile_picture=profile_picture, userid=userid, fname=fname, lname=lname, dob=dob, collegename=collegename, departmentname=departmentname, semester=semester, section=section, email=email, phonenumber=phonenumber, batch=batch, LEET=LEET)
        else:
            flash('User not found.', 'error')
            return redirect(url_for('.index'))
    else:
        flash('Pending account verification.', 'alert')
        return redirect(url_for('.login'))
    
#################################### Route for Student Dashboard End  ####################################
    

#################################### Route for Faculty Dashboard Start  ####################################

@routes_bp.route('/facultydashboard')
def facultydashboard():
    if 'logged_in' in session:
        userid = session['userid']
        db_file = 'FacultyMember.db'
        db_path = os.path.join(DATABASE_FOLDER, db_file)
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT * FROM users WHERE userid=?", (userid,))
        user = c.fetchone()

        if user:
            profile_picture = user[8]
            userid = user[1]
            fname = user[2]  
            lname = user[3]  
            role = user[7]
            designation = user[13]
            collegename = user[5]  
            departmentname = user[6]  

            semester_section = {} 
            semester_subject = {} 
            
            conn.close()

            if collegename == 'Chandigarh Engineering College':
                if departmentname == 'Electronics and Communication Engineering':
                    if role == 'Class Counselor':
                        db_folder = os.path.join('database', 'Chandigarh Engineering College', 'Electronics and Communication Engineering')
                        db_path = os.path.join(db_folder, 'CC.db')
                    
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                    
                        c.execute("SELECT class, batch FROM class_Counselor WHERE userid=?", (userid,))
                        cc_details = c.fetchall()
                        semester_section = {}

                        for detail in cc_details:
                            class_info = detail[0].split('_')
                            semester = class_info[0]
                            section = class_info[1]
                            batch = detail[1]

                            if semester in semester_section:
                                if batch in semester_section[semester]:
                                    semester_section[semester][batch].append(section)
                                else:
                                    semester_section[semester][batch] = [section]
                            else:
                                semester_section[semester] = {batch: [section]}

                        



                        db_folder = os.path.join('database', 'Chandigarh Engineering College', 'Electronics and Communication Engineering')
                        db_path = os.path.join(db_folder, 'Instructor.db')
                    
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                    
                        c.execute("SELECT class, batch FROM instructor_details WHERE userid=?", (userid,))
                        instructor_details = c.fetchall()

                        for ins_detail in instructor_details:
                            ins_class_info = ins_detail[0].split('_')
                            ins_semester = ins_class_info[0]
                            ins_section = ins_class_info[1]
                            ins_subject = ins_class_info[2] 
                            ins_batch = ins_detail[1]

    
                            if ins_semester not in semester_subject:
        
                               semester_subject[ins_semester] = []

    
                            semester_subject[ins_semester].append({'section': ins_section, 'subject': ins_subject, 'batch': ins_batch})


                        conn.close()

                    elif role == 'Instructor':
                        
                        db_folder = os.path.join('database', 'Chandigarh Engineering College', 'ECE')
                        db_path = os.path.join(db_folder, 'Instructor.db')
                    
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                    
                        c.execute("SELECT class FROM instructor_details WHERE userid=?", (userid,))
                        instructor_details = c.fetchall()

                        for ins_detail in instructor_details:
                            ins_class_info = ins_detail[0].split('_')
                            ins_semester = ins_class_info[0]
                            ins_section = ins_class_info[1]
                            ins_subject = ins_class_info[2] 

    
                            if ins_semester not in semester_subject:
        
                               semester_subject[ins_semester] = []

    
                            semester_subject[ins_semester].append({'section': ins_section, 'subject': ins_subject})


                        conn.close()

                        

                    
                        
                    else:
                        flash('Invalid role', 'error')
                        return redirect(url_for('.facultydashboard'))
            else:
                flash('Invalid college or department name', 'error')
                return redirect(url_for('.login'))

            return render_template('facultydashboard.html', profile_picture=profile_picture, userid=userid, fname=fname, lname=lname, role=role, designation=designation, collegename=collegename, departmentname=departmentname, semester_section=semester_section, semester_subject=semester_subject, get_semester_postfix=get_semester_postfix, ins_semester_postfix=ins_semester_postfix)


        else:
            flash('User not found.', 'error')
            return redirect(url_for('.index'))
    else:
        flash('Pending account verification.', 'alert')
        return redirect(url_for('.login'))
    
    
############# Functions for semester postfix Start  #############

def get_semester_postfix(semester_num):
    if semester_num == "1":
        return 'st'
    elif semester_num == "2":
        return 'nd'
    elif semester_num == "3":
        return 'rd'
    else:
        return 'th'
    
def ins_semester_postfix(semester_num):
    if semester_num == "1":
        return 'st'
    elif semester_num == "2":
        return 'nd'
    elif semester_num == "3":
        return 'rd'
    else:
        return 'th'
    
############# Functions for semester postfix End  #############
    
#################################### Route for Faculty Dashboard End  ####################################


##################### Route for Updating faculty details Start  #####################

@routes_bp.route('/update_faculty', methods=['POST'])
def update_faculty():
    if request.method == 'POST':
        try:
            userid = request.form['userid']
            fname = request.form['fname']
            lname = request.form['lname']
            designation = request.form['designation']
            role = request.form['role']
            collegename = request.form['collegename']
            departmentname = request.form['departmentname']
            
            db_path = os.path.join(DATABASE_FOLDER, 'FacultyMember.db')
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("""
                UPDATE users 
                SET fname=?, lname=?, designation=?, role=?, collegename=?, departmentname=?
                WHERE userid=?
            """, (fname, lname, designation, role, collegename, departmentname, userid))
            conn.commit()
            conn.close()
            
            return redirect(url_for('.facultydashboard'))
        except Exception as e:
            print(f"Error updating faculty: {e}")
            flash('An error occurred while updating faculty information.', 'error')
            return redirect(url_for('.facultydashboard'))
        
##################### Route for Updating faculty details End  #####################


##################### Route for Updating student details Start  #####################

@routes_bp.route('/update_student', methods=['POST'])
def update_student():
    if request.method == 'POST':
        try:
            userid = request.form['userid']
            fname = request.form['fname']
            lname = request.form['lname']
            dob = request.form['dob']
            email = request.form['email']
            phonenumber = request.form['phonenumber']
            collegename = request.form['collegename']
            departmentname = request.form['departmentname']
            semester = request.form['semester']
            section = request.form['section']
            LEET = request.form['leetStudent']
            start_year = int(request.form['startYear'])
            end_year = int(request.form['endYear'])

            if LEET == 'yes':
                start_year -= 1

            batch = f"{start_year}-{end_year}"
            
            db_path = os.path.join(DATABASE_FOLDER, 'Students.db')
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("""
                UPDATE users 
                SET fname=?, lname=?, dob=?, email=?, phonenumber=?, collegename=?, departmentname=?, LEET=?, batch=?, semester=?, section=?
                WHERE userid=?
            """, (fname, lname, dob, email, phonenumber, collegename, departmentname, LEET, batch, semester, section, userid))
            conn.commit()
            conn.close()
            
            flash('Student information updated successfully.', 'success')
            return redirect(url_for('.studentdashboard'))
        except Exception as e:
            print(f"Error updating student: {e}")
            flash('An error occurred while updating student information.', 'error')
            return redirect(url_for('.studentdashboard'))
        
##################### Route for Updating student details End  #####################


# #################################### Route to fetch similar faculty Start  ####################################

# @routes_bp.route('/fetch_similar_faculty', methods=['GET'])
# def fetch_similar_faculty():
#     if 'user_data' in session:
#         user_data = session['user_data']
#         collegename = user_data['collegename']
#         departmentname = user_data['departmentname']
#         userid = session['userid']  
        
#         db_path = os.path.join(DATABASE_FOLDER, 'FacultyMember.db')
#         conn = sqlite3.connect(db_path)
#         c = conn.cursor()
#         c.execute("SELECT fname, lname, role, profile_picture, designation FROM users WHERE collegename=? AND departmentname=? AND userid!=?", (collegename, departmentname, userid))
#         faculty_members = c.fetchall()
#         conn.close()
        
#         return jsonify(faculty_members)
#     else:
#         return jsonify({'error': 'User data not found'})
    
# #################################### Route to fetch similar faculty End  ####################################
    

#################################### Route to save class details for CC, AC, HOD, TPP Start  ####################################

@routes_bp.route('/class_details', methods=['POST'])
def class_details():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        role = user_data['role']
        userid = session['userid']

        CC_DB = os.path.join('database', collegename, departmentname, 'CC.db')

        os.makedirs(os.path.dirname(CC_DB), exist_ok=True) #make all directories, if not exist

        if role == 'Class Counselor':
                
                semester = request.form.get('semester')
                section = request.form.get('section')
                start_year = request.form.get('startYear')
                end_year = request.form.get('endYear')

                if None in [semester, section, start_year, end_year]:
                    flash('Please select all fields.', 'error')
                else:
                    batch = f"{start_year}-{end_year}"
                    conn = sqlite3.connect(CC_DB)
                    c = conn.cursor()
                    c.execute("SELECT id FROM class_counselor WHERE userid = ? AND class LIKE ? AND batch = ?",
                              (userid, f"{semester}_%", batch))
                    existing_record = c.fetchone()

                    if existing_record:
                        c.execute("UPDATE class_counselor SET class = ? WHERE userid = ? AND class LIKE ? AND batch = ?",
                                  (f"{semester}_{section}", userid, f"{semester}_%", batch))
                    else:
                        c.execute("INSERT INTO class_counselor (userid, class, batch) VALUES (?, ?, ?)",
                                  (userid, f"{semester}_{section}", batch))

                    conn.commit()
                    conn.close()

                    return redirect(url_for('.facultydashboard'))

        return redirect(url_for('.login'))

    else:
        flash('User not logged in.', 'error')
        return redirect(url_for('.login'))
    
#################################### Route to save class details for CC, AC, HOD, TPP End  ####################################


#################################### Route to save class details for Instructor Start  ####################################
    
@routes_bp.route('/instructor_details', methods=['POST'])
def instructor_details():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        userid = session['userid']

        semester = request.form.get('semester')
        section = request.form.get('section')
        subject = request.form.get('subject')
        startYear = request.form.get('startYear')
        endYear = request.form.get('endYear')
        batch = f"{startYear}-{endYear}"

        if not semester or not section or not subject:
            flash('Please select semester, section, and subject.', 'error')
            return redirect(url_for('.facultydashboard'))

        INS_DB = os.path.join('database', collegename, departmentname, 'Instructor.db')

        os.makedirs(os.path.dirname(INS_DB), exist_ok=True) #make all directories, if not exist

        conn = sqlite3.connect(INS_DB)
        c = conn.cursor()

        c.execute("INSERT INTO instructor_details (userid, class, subject, batch) VALUES (?, ?, ?, ?)", (userid, f"{semester}_{section}_{subject}", subject, batch))

        conn.commit()
        conn.close()

        flash('Instructor details stored successfully!', 'success')
        return redirect(url_for('.facultydashboard'))
    else:
        flash('User not logged in.', 'error')
        return redirect(url_for('.login'))
    
#################################### Route to save class details for Instructor End  ####################################


#################################### Route to fetch students for CC, AC, HOD, TPP Start  ################################

@routes_bp.route('/fetch_students', methods=['GET'])
def fetch_students():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        semester = request.args.get('semester')
        section = request.args.get('section')
        batch = request.args.get('batch')
        
        db_path = os.path.join(DATABASE_FOLDER, 'Students.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT fname, lname, dob, semester, section, profile_picture, phonenumber, email, userid, verified FROM users WHERE collegename=? AND departmentname=? AND semester=? AND section=? AND batch=?", (collegename, departmentname, semester, section, batch))
        students = c.fetchall()
        conn.close()
        
        formatted_students = [{'fname': student[0], 'lname': student[1], 'dob': student[2], 'semester': student[3], 'section': student[4], 'profile_picture': student[5], 'phonenumber': student[6], 'email': student[7], 'userid': student[8], 'verified': student[9]} for student in students]
        
        return jsonify({'students': formatted_students})
    else:
        return jsonify({'error': 'User data not found'})
    

#################################### Route to fetch students for CC, AC, HOD, TPP End  ################################


#################################### Route to fetch students for Instructor Start  ####################################
    
@routes_bp.route('/fetch_students_for_instructor', methods=['GET'])
def fetch_students_for_instructor():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        semester = request.args.get('semester')
        section = request.args.get('section')
        batch = request.args.get('batch')
        
        db_path = os.path.join(DATABASE_FOLDER, 'Students.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        if len(section) > 1 and section[-1].isdigit():
            c.execute("SELECT fname, lname, dob, semester, section, profile_picture, phonenumber, email, userid FROM users WHERE collegename=? AND departmentname=? AND semester=? AND section=? AND batch=?", (collegename, departmentname, semester, section, batch))
        else:
            c.execute("SELECT fname, lname, dob, semester, section, profile_picture, phonenumber, email, userid FROM users WHERE collegename=? AND departmentname=? AND semester=? AND section LIKE ? AND batch=?", (collegename, departmentname, semester, section + '%', batch))

        students = c.fetchall()
        conn.close()
        
        formatted_students = [{'fname': student[0], 'lname': student[1], 'dob': student[2], 'semester': student[3], 'section': student[4], 'profile_picture': student[5], 'phonenumber': student[6], 'email': student[7], 'userid': student[8]} for student in students]
        
        return jsonify({'students': formatted_students})
    else:
        return jsonify({'error': 'User data not found'})
    
#################################### Route to fetch students for Instructor End  ####################################


#################################### Route to fetch students for MST Marks Start  ####################################
    
@routes_bp.route('/fetch_students_for_MST_marks', methods=['GET'])
def fetch_students_for_MST_marks():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        semester = request.args.get('semester')
        section = request.args.get('section')
        batch = request.args.get('batch')
        
        db_path = os.path.join(DATABASE_FOLDER, 'Students.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        if len(section) > 1 and section[-1].isdigit():
            c.execute("SELECT fname, lname, dob, semester, section, profile_picture, phonenumber, email, userid FROM users WHERE collegename=? AND departmentname=? AND semester=? AND section=? AND batch=?", (collegename, departmentname, semester, section, batch))
        else:
            c.execute("SELECT fname, lname, dob, semester, section, profile_picture, phonenumber, email, userid FROM users WHERE collegename=? AND departmentname=? AND semester=? AND section LIKE ? AND batch=?", (collegename, departmentname, semester, section + '%', batch))

        students = c.fetchall()
        conn.close()
        
        formatted_students = [{'fname': student[0], 'lname': student[1], 'dob': student[2], 'semester': student[3], 'section': student[4], 'profile_picture': student[5], 'phonenumber': student[6], 'email': student[7], 'userid': student[8]} for student in students]
        
        return jsonify({'students': formatted_students})
    else:
        return jsonify({'error': 'User data not found'})
    
#################################### Route to fetch students for MST Marks End  ####################################


#################################### Route to fetch students for Assignment Start  ####################################
    
@routes_bp.route('/fetch_students_for_assignment', methods=['GET'])
def fetch_students_for_assignment():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        semester = request.args.get('semester')
        section = request.args.get('section')
        batch = request.args.get('batch')
        
        db_path = os.path.join(DATABASE_FOLDER, 'Students.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        if len(section) > 1 and section[-1].isdigit():
            c.execute("SELECT fname, lname, dob, semester, section, profile_picture, phonenumber, email, userid FROM users WHERE collegename=? AND departmentname=? AND semester=? AND section=? AND batch=?", (collegename, departmentname, semester, section, batch))
        else:
            c.execute("SELECT fname, lname, dob, semester, section, profile_picture, phonenumber, email, userid FROM users WHERE collegename=? AND departmentname=? AND semester=? AND section LIKE ? AND batch=?", (collegename, departmentname, semester, section + '%', batch))

        students = c.fetchall()
        conn.close()
        
        formatted_students = [{'fname': student[0], 'lname': student[1], 'dob': student[2], 'semester': student[3], 'section': student[4], 'profile_picture': student[5], 'phonenumber': student[6], 'email': student[7], 'userid': student[8]} for student in students]
        
        return jsonify({'students': formatted_students})
    else:
        return jsonify({'error': 'User data not found'})
    
#################################### Route to fetch students for Assignment End  ####################################
    

#################################### Route to delete class details Start  ####################################

@routes_bp.route('/delete_class_details', methods=['DELETE'])
def delete_class_details():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        role = user_data['role']
        userid = session['userid']

        if request.method == 'DELETE':
            semester = request.args.get('semester')
            section = request.args.get('section')
            subject = request.args.get('subject')
        
            INS_DB = os.path.join('database', collegename, departmentname, 'Instructor.db')

            CC_DB = os.path.join('database', collegename, departmentname, 'CC.db')

            ################################ Instructor (which includes CC, AC, HOD) ################################
            if role in ['Class Counselor', 'Academic Coordinator', 'Head of Department', 'Instructor']:
                      
                    try:
                        conn = sqlite3.connect(INS_DB)
                        c = conn.cursor()

                        if section.endswith(('1', '2')):
    
                            section_chars = ''.join(filter(str.isalpha, section))
                            section_digits = ''.join(filter(str.isdigit, section))
                            class_string = f"{semester}_{section_chars}{section_digits}_{subject}"
                        else:
                            class_string = f"{semester}_{section}_{subject}"
                          
                          
                        c.execute("DELETE FROM instructor_details WHERE userid=? AND class=? AND subject=?", 
                                (userid, class_string, subject))


                        if role == 'Class Counselor':
                            CCDB_PATH = os.path.join(CC_DB)
                            cc_conn = sqlite3.connect(CCDB_PATH)
                            cc_c = cc_conn.cursor()
                            cc_c.execute("DELETE FROM class_counselor WHERE userid=? AND class=?", (userid, f"{semester}_{section}"))
                            cc_conn.commit()
                            cc_conn.close()

                        conn.commit()
                        conn.close()

                        return jsonify({'success': True}), 200
                    except sqlite3.Error as e:
                        print("SQLite error:", e)
                        return jsonify({'error': str(e)}), 500
                      
#################################### Route to delete class details End  ####################################


######################################## Fetch Students For Attendance Start ########################################

@routes_bp.route('/fetch_students_for_attendance', methods=['GET'])
def fetch_students_for_attendance():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        semester = request.args.get('semester')
        section = request.args.get('section')
        batch = request.args.get('batch')
        
        db_path = os.path.join(DATABASE_FOLDER, 'Students.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        if len(section) > 1 and section[-1].isdigit():
            c.execute("SELECT fname, lname, semester, section, profile_picture, userid, batch FROM users WHERE collegename=? AND departmentname=? AND semester=? AND section=? AND batch=?", (collegename, departmentname, semester, section, batch))
        else:
            c.execute("SELECT fname, lname, semester, section, profile_picture, userid, batch FROM users WHERE collegename=? AND departmentname=? AND semester=? AND section LIKE ? AND batch=?", (collegename, departmentname, semester, section + '%', batch))

        students = c.fetchall()
        conn.close()
        
        formatted_students = [{'fname': student[0], 'lname': student[1], 'semester': student[2], 'section': student[3], 'profile_picture': student[4], 'userid': student[5], 'batch': student[6]} for student in students]
        
        return jsonify({'students': formatted_students})
    else:
        return jsonify({'error': 'User data not found'})

######################################## Fetch Students For Attendance End ########################################


######################################## Mark Student Attendance Start #######################################

@routes_bp.route('/save_attendance', methods=['POST'])
def save_attendance_route():
    try:
        attendance_data = request.json
        save_attendance(attendance_data)
        return jsonify({'message': 'Attendance data saved successfully'})
    except Exception as e:
        print("Error processing attendance data:", e)
        return jsonify({'error': 'Failed to save attendance data'}), 500

def save_attendance(student_data):
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        batch = student_data.get('batch')
        subject = student_data.get('subject')
        semester = student_data.get('semester')
        selected_date = student_data.get('date', '')

        try:

            # Build the database path
            batch_db = batch.replace(' ', '_')
            ATTENDANCE_DB = os.path.join(DATABASE_FOLDER, collegename, departmentname, batch_db, semester, 'Attendance', f'{subject}.db')
            
            os.makedirs(os.path.dirname(ATTENDANCE_DB), exist_ok=True)

            with sqlite3.connect(ATTENDANCE_DB) as conn:
                cursor = conn.cursor()

                cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
                                    name TEXT,
                                    roll_number INTEGER,
                                    semester TEXT,
                                    section TEXT,
                                    subject TEXT
                                )''')

                cursor.execute("PRAGMA table_info(attendance)")
                columns = [column[1] for column in cursor.fetchall()]

                if selected_date not in columns:
                    cursor.execute(f"ALTER TABLE attendance ADD COLUMN '{selected_date}' TEXT DEFAULT NULL")

                if isinstance(student_data, dict):
                    name = student_data.get('name', '')
                    roll_number = student_data.get('roll_number', '')
                    semester = student_data.get('semester', '')
                    section = student_data.get('section', '')
                    batch = student_data.get('batch', '')
                    subject = student_data.get('subject', '')
                    present = 'Present' if student_data.get('present', False) else 'Absent'

                    cursor.execute("SELECT * FROM attendance WHERE roll_number = ? AND subject = ?", (roll_number, subject))
                    existing_attendance = cursor.fetchone()

                    if existing_attendance:
                        cursor.execute(f"UPDATE attendance SET '{selected_date}' = ? WHERE roll_number = ? AND subject = ?", (present, roll_number, subject))
                    else:
                        cursor.execute(f"INSERT INTO attendance (name, roll_number, semester, section, subject, '{selected_date}') VALUES (?, ?, ?, ?, ?, ?)", (name, roll_number, semester, section, subject, present))
                else:
                    print("Invalid data format for student")

        except sqlite3.Error as e:
            print("SQLite error:", e)
        except Exception as e:
            print("Error saving attendance data:", e)

######################################## Mark Student Attendance End ########################################


######################################## Saving MST Marks Start #######################################

@routes_bp.route('/save_mst_marks', methods=['POST'])
def save_mst_marks():
    try:
        marks_data = request.json
        save_marks(marks_data)
        return jsonify({'message': 'MST marks saved successfully'})
    except Exception as e:
        print("Error processing MST marks data:", e)
        return jsonify({'error': 'Failed to save MST marks data'}), 500

def save_marks(marks_data):
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        batch = marks_data.get('batch')
        subject = marks_data.get('subject')
        semester = marks_data.get('semester')

        try:
                    
            # Build the database path
            batch_db = batch.replace(' ', '_')
            MARKS_DB = os.path.join(DATABASE_FOLDER, collegename, departmentname, batch_db, semester, 'MST_Marks', f'{subject}.db')

            os.makedirs(os.path.dirname(MARKS_DB), exist_ok=True)

            with sqlite3.connect(MARKS_DB) as conn:
                cursor = conn.cursor()

                cursor.execute('''CREATE TABLE IF NOT EXISTS marks (
                                    name TEXT,
                                    roll_number INTEGER,
                                    semester TEXT,
                                    section TEXT,
                                    mst1 INTEGER,
                                    mst2 INTEGER
                                )''')

                if 'students' in marks_data:
                    for student in marks_data['students']:
                        cursor.execute("SELECT * FROM marks WHERE roll_number = ?", (student['roll_number'],))
                        existing_student = cursor.fetchone()

                        if existing_student:
                            cursor.execute("UPDATE marks SET mst1 = ?, mst2 = ? WHERE roll_number = ?", (student['mst1'], student['mst2'], student['roll_number']))
                        else:
                            cursor.execute("INSERT INTO marks (name, roll_number, semester, section, mst1, mst2) VALUES (?, ?, ?, ?, ?, ?)", 
                                            (student['name'], student['roll_number'], student['semester'], student['section'], student['mst1'], student['mst2']))

        except sqlite3.Error as e:
            print("SQLite error:", e)
        except Exception as e:
            print("Error saving marks data:", e)

######################################## Saving MST Marks End ########################################


######################################## Fetch Existing MST Marks #######################################

@routes_bp.route('/fetch_existing_mst_marks', methods=['GET'])
def fetch_existing_mst_marks():
    try:
        if 'user_data' not in session:
            return jsonify({'error': 'User data not found in session'}), 400

        user_data = session['user_data']
        collegename = user_data.get('collegename')
        departmentname = user_data.get('departmentname')
        semester = request.args.get('semester')
        section = request.args.get('section')
        batch = request.args.get('batch')
        subject = request.args.get('subject')
        roll_number = request.args.get('rollNumber')

        if not all([collegename, departmentname, semester, section, batch, subject, roll_number]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Build the database path
        batch_db = batch.replace(' ', '_')
        MARKS_DB = os.path.join(DATABASE_FOLDER, collegename, departmentname, batch_db, semester, 'MST_Marks', f'{subject}.db')

        marks_data = {}
        try:
            with sqlite3.connect(MARKS_DB) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='marks'")
                if cursor.fetchone():
                    cursor.execute(
                        "SELECT mst1, mst2 FROM marks WHERE roll_number = ? AND semester = ? AND section = ?",
                        (roll_number, semester, section)
                    )
                    existing_marks = cursor.fetchone()
                    if existing_marks:
                        marks_data[roll_number] = {'mst1': existing_marks[0], 'mst2': existing_marks[1]}
                    else:
                        marks_data[roll_number] = {'mst1': None, 'mst2': None}
        except sqlite3.Error as e:
            print("SQLite error:", e)
            return jsonify({'error': 'Database error occurred'}), 500

        return jsonify(marks_data)

    except Exception as e:
        print("Error fetching existing marks data:", e)
        return jsonify({'error': 'An unexpected error occurred'}), 500
    
######################################## Fetch Existing Assignment Status ##################################################

@routes_bp.route('/fetch_existing_assignment_status', methods=['GET'])
def fetch_existing_assignment_status():
    try:
        roll_number = request.args.get('rollNumber')
        batch = request.args.get('batch')
        subject = request.args.get('subject')
        semester = request.args.get('semester')

        if 'user_data' in session:
            user_data = session['user_data']
            collegename = user_data['collegename']
            departmentname = user_data['departmentname']

            batch_db = batch.replace(' ', '_')
            ASSIGNMENT_DB = os.path.join(DATABASE_FOLDER, collegename, departmentname, batch_db, semester, 'Assignment', f'{subject}.db')

            with sqlite3.connect(ASSIGNMENT_DB) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM marks WHERE roll_number = ?", (roll_number,))
                row = cursor.fetchone()
                if row:
                    columns = [column[0] for column in cursor.description]
                    assignment_status = dict(zip(columns, row))
                    return jsonify({roll_number: assignment_status})
                else:
                    return jsonify({'message': 'No data found for the given roll number'}), 200
                
        return jsonify({'error': 'Failed to fetch assignment status'}), 500
    
    except Exception as e:

        print("Error fetching assignment status:", e)

        return jsonify({'error': 'Failed to fetch assignment status'}), 500



######################################## Fetching Student Attendance Status Start ########################################

@routes_bp.route('/check_attendance_existence', methods=['GET'])
def check_attendance_existence():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        batch = request.args.get('batch')
        semester = request.args.get('semester')
        subject = request.args.get('subject')
        rollNumber = request.args.get('rollNumber')
        selectedDate = request.args.get('selectedDate')

    # Build the database path
    batch_db = batch.replace(' ', '_')
    ATTENDANCE_DB = os.path.join(DATABASE_FOLDER, collegename, departmentname, batch_db, semester, 'Attendance', f'{subject}.db')

    try:
        conn = sqlite3.connect(ATTENDANCE_DB)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(attendance)")
        columns = cursor.fetchall()
        selected_date_column_index = None

        for index, column in enumerate(columns):
            if column[1] == selectedDate:
                selected_date_column_index = index
                break

        cursor.execute(f"SELECT * FROM attendance WHERE roll_number = ? AND subject = ? AND semester = ?", (rollNumber, subject, semester))
        student_attendance_data = cursor.fetchone()

        if student_attendance_data:
            attendance_status = student_attendance_data[selected_date_column_index]
            return jsonify({'rollNumber': rollNumber, 'attendanceStatus': attendance_status})
        else:
            return jsonify({'error': 'No attendance data found for the roll number'})

    except Exception as e:
        print("Error:", e)
        return jsonify({'error': str(e)})
    finally:
        if conn:
            conn.close()

######################################## Saving Assignment Start #######################################

@routes_bp.route('/save_assignment', methods=['POST'])
def save_assignment():
    try:
        assignment_data = request.json
        save_data(assignment_data)
        return jsonify({'message': 'Assignment status saved successfully'})
    except Exception as e:
        print("Error processing assignment data:", e)
        return jsonify({'error': 'Failed to save assignment status'}), 500

def save_data(assignment_data):
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        batch = assignment_data.get('batch')
        subject = assignment_data.get('subject')
        semester = assignment_data.get('semester')

        try:
            
            batch_db = batch.replace(' ', '_')
            ASSIGNMENT_DB = os.path.join(DATABASE_FOLDER, collegename, departmentname, batch_db, semester, 'Assignment', f'{subject}.db')

            os.makedirs(os.path.dirname(ASSIGNMENT_DB), exist_ok=True)

            with sqlite3.connect(ASSIGNMENT_DB) as conn:
                cursor = conn.cursor()

                cursor.execute('''CREATE TABLE IF NOT EXISTS marks (
                                    name TEXT,
                                    roll_number INTEGER PRIMARY KEY,
                                    semester TEXT,
                                    section TEXT,
                                    assignment1 TEXT,
                                    assignment2 TEXT
                                )''')

                if 'students' in assignment_data:
                    for student in assignment_data['students']:
                        assignment1 = student.get('assignment1', 'Not Submitted')
                        assignment2 = student.get('assignment2', 'Not Submitted')
                        roll_number = student['roll_number']

                        cursor.execute("SELECT * FROM marks WHERE roll_number = ?", (roll_number,))
                        existing_student = cursor.fetchone()

                        if existing_student:
                            cursor.execute("UPDATE marks SET assignment1 = ?, assignment2 = ? WHERE roll_number = ?", 
                                            (assignment1, assignment2, roll_number))
                        else:
                            cursor.execute("INSERT INTO marks (name, roll_number, semester, section, assignment1, assignment2) VALUES (?, ?, ?, ?, ?, ?)", 
                                            (student['name'], roll_number, student['semester'], student['section'], assignment1, assignment2))
                conn.commit()

        except sqlite3.Error as e:
            print("SQLite error:", e)
        except Exception as e:
            print("Error saving assignment data:", e)

######################################## Saving Assignment End ########################################


######################################## Fetching Student's Subject Attendance For Student Dashboard ########################################

@routes_bp.route('/my_attendances', methods=['GET'])
def my_attendances():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        batch = request.args.get('batch')
        semester = request.args.get('semester')
        subject = request.args.get('subject')
        rollNumber = request.args.get('rollNumber')

    batch_db = batch.replace(' ', '_')
    ATTENDANCE_DB = os.path.join(DATABASE_FOLDER, collegename, departmentname, batch_db, semester, 'Attendance', f'{subject}.db')

    try:
        conn = sqlite3.connect(ATTENDANCE_DB)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(attendance)")
        columns = cursor.fetchall()

        cursor.execute(f"SELECT * FROM attendance WHERE roll_number = ? AND subject = ? AND semester = ?", (rollNumber, subject, semester))
        student_attendance_data = cursor.fetchone()

        if student_attendance_data:
            attendance_data_by_date = {}
            for index, data in enumerate(student_attendance_data):
                if index not in range(0, 5):  
                    date = columns[index][1] 
                    attendance_data_by_date[date] = data

            return jsonify({'rollNumber': rollNumber, 'attendanceData': attendance_data_by_date})
        else:
            return jsonify({'error': 'No attendance data found for the roll number'})

    except Exception as e:
        print("Error:", e)
        return jsonify({'error': str(e)})
    finally:
        if conn:
            conn.close()


######################################## Fetching Student's Subject Assignment For Student Dashboard ########################################






######################################## Fetching Student Subject MST Marks For Student Dashboard ########################################

@routes_bp.route('/my_mst_marks', methods=['GET'])
def my_mst_marks():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        rollNumber = request.args.get('rollNumber')
        subject = request.args.get('subject')
        semester = request.args.get('semester')
        batch = request.args.get('batch')

        # Build the database path
        batch_db = batch.replace(' ', '_')
        MARKS_DB = os.path.join(DATABASE_FOLDER, collegename, departmentname, batch_db, semester, 'MST_Marks', f'{subject}.db')

        try:
            conn = sqlite3.connect(MARKS_DB)
            cursor = conn.cursor()

            cursor.execute(f"SELECT * FROM marks WHERE roll_number = ?", (rollNumber,))
            student_mst_marks_data = cursor.fetchone()

            if student_mst_marks_data:
                mst1_index = 4
                mst2_index = 5
                return jsonify({subject: {'mst1': student_mst_marks_data[mst1_index], 'mst2': student_mst_marks_data[mst2_index]}})
            else:
                return jsonify({'error': 'No MST marks data found for the roll number'})

        except Exception as e:
            print("Error:", e)
            return jsonify({'error': str(e)})
        finally:
            if conn:
                conn.close()
    else:
        return jsonify({'error': 'User session data not found'})
    


######################################## Fetching Student Subject MST Marks For Student Dashboard ########################################

@routes_bp.route('/my_assignment', methods=['GET'])
def my_assignment():
    if 'user_data' in session:
        user_data = session['user_data']
        collegename = user_data['collegename']
        departmentname = user_data['departmentname']
        rollNumber = request.args.get('rollNumber')
        subject = request.args.get('subject')
        semester = request.args.get('semester')
        batch = request.args.get('batch')

        batch_db = batch.replace(' ', '_')
        ASSIGNMENT_DB = os.path.join(DATABASE_FOLDER, collegename, departmentname, batch_db, semester, 'Assignment', f'{subject}.db')

        try:
            conn = sqlite3.connect(ASSIGNMENT_DB)
            cursor = conn.cursor()

            cursor.execute(f"SELECT * FROM marks WHERE roll_number = ?", (rollNumber,))
            student_assignment_data = cursor.fetchone()

            if student_assignment_data:
                assignment1_index = 4
                assignment2_index = 5
                return jsonify({subject: {'assignment1': student_assignment_data[assignment1_index], 'assignment2': student_assignment_data[assignment2_index]}})
            else:
                return jsonify({'error': 'No Assignment marks data found for the roll number'})

        except Exception as e:
            print("Error:", e)
            return jsonify({'error': str(e)})
        finally:
            if conn:
                conn.close()
    else:
        return jsonify({'error': 'User session data not found'})
    


######################################## Route for Subjects Start ########################################

@routes_bp.route('/subjects/<department>/<semester>')
def get_subjects(department, semester):
    subjects = subjects_data.get(department, {}).get(semester, [])
    return jsonify({'subjects': subjects})


subjects_data = {
    'Electronics and Communication Engineering': {
        '1': [],
        '2': [],
        '3': ['Electronic Devices', 'Digital System Design', 'Electromagnetic Waves', 'Network Theory', 'Mathematics III', 'Electronic Devices Laboratory', 'Digital System Design Laboratory', 'Foundational Course in Humanities: Development of Societies or Philosophy', '4-Week Institutional Training', 'Mentoring and Professional Development'],
        '4': ['Analog Circuits', 'Microprocessors and Microcontrollers', 'Data Structures and Algorithms', 'Signals and Systems', 'Universal Human Values: Understanding Harmony', 'Environmental Sciences', 'Analog Circuits Laboratory', 'Microprocessors and Microcontroller Laboratory', 'Mentoring and Professional Development'],
        '5': ['Analog and Digital Communication', 'Digital Signal Processing', 'Linear Integrated Circuits', 'Control Systems', 'Java', 'Project Management', 'Analog and Digital Communication Laboratory', 'Digital Signal Processing Laboratory', 'Linear Integrated Circuits Laboratory', 'Java Laboratory', 'Mentoring and Professional Development'],
        '6': ['Wireless Communication', 'Computer Networks', 'Optical Fibers and Communication', 'Microwave and Antenna Engineering', 'C Sharp', 'Operating Systems', 'Project-1', 'Optical Fibers and Communication Laboratory', 'Microwave and Antenna Engineering Laboratory', 'C Sharp Laboratory']

    },
    'Other': {
        '1': [],
        '2': []
    }
}

######################################## Route for Subjects End ########################################


######################################## Route for AI Attendance Start ########################################

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("static/aiAttendance/shape_predictor_68_face_landmarks.dat")
face_rec_model = dlib.face_recognition_model_v1("static/aiAttendance/dlib_face_recognition_resnet_model_v1.dat")

known_face_encodings = []
known_names = []

static_folder = 'static/ProfilePictures/Student'

detected_names = set()


class VideoCamera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        # self.cap = cv2.VideoCapture('http://192.168.4.1/cam-stream')
    
    def __del__(self):
        self.cap.release()

    def get_frame(self):
        ret, frame = self.cap.read()
        frame = cv2.resize(frame, (640, 480))
        if ret:
            self.process_frame(frame)
            ret, jpeg = cv2.imencode('.jpg', frame)
            return jpeg.tobytes()

    def process_frame(self, frame):
        global detected_names
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray, 0)
        if len(faces) != 0:
            for rect in faces:
                shape = predictor(gray, rect)
                face_encoding = np.array(face_rec_model.compute_face_descriptor(frame, shape))
                distances = np.linalg.norm(known_face_encodings - face_encoding, axis=1)
                min_distance = min(distances)
                if min_distance < 0.6:
                    index = distances.argmin()
                    name = known_names[index]
                    detected_names.add(name)
                    
                    
                    
                    cv2.rectangle(frame, (rect.left(), rect.top()), (rect.right(), rect.bottom()), (0, 255, 0), 2)
                else:
                    detected_names.add("Unknown")
                    cv2.rectangle(frame, (rect.left(), rect.top()), (rect.right(), rect.bottom()), (0, 0, 255), 2)
                    cv2.putText(frame, "Unknown", (rect.left(), rect.top() - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

@routes_bp.route('/detected_names', methods=['GET'])
def get_detected_names():
    global detected_names
    filtered_names = list(detected_names - {"Unknown"})
    detected_names.clear()
    return jsonify({"names": filtered_names})

@routes_bp.route('/ai_attendance', methods=['POST'])
def ai_attendance():
    try:
        data = request.json
        roll_numbers = data['rollNumbers']
        
        known_face_encodings.clear()
        known_names.clear()

        for filename in os.listdir(static_folder):
            if any(roll_number in filename for roll_number in roll_numbers):
                name = os.path.splitext(filename)[0].replace('_', ' ')
                file_path = os.path.join(static_folder, filename)
                img = cv2.imread(file_path)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = detector(gray, upsample_num_times=1)
                for rect in faces:
                    shape = predictor(gray, rect)
                    face_encoding = np.array(face_rec_model.compute_face_descriptor(img, shape))
                    known_face_encodings.append(face_encoding.tolist())  
                    known_names.append(name)
        
        return jsonify({'message': 'received'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@routes_bp.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()), mimetype='multipart/x-mixed-replace; boundary=frame')

######################################## Route for AI Attendance End ########################################


######################################## Route for Notes Uploading START ########################################

UPLOAD_FOLDER_NOTES = os.path.join(os.getcwd(), 'static', 'Assets', 'Notes')
ALLOWED_NOTES = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'ppt', 'pptx', 'doc', 'docx', 'xls', 'xlsx', 'webp'}

def generate_unique_id_notes():
    return str(uuid.uuid4().hex[:4])

def calculate_file_hash_notes(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def allowed_file_notes(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_MST

@routes_bp.route('/upload_note', methods=['POST'])
def upload_note():
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'})

    files = request.files.getlist('files')
    subject = request.form.get('subject')

    uploaded_files = []
    for file in files:
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No selected file'})

        if file and allowed_file_notes(file.filename):
            filename = file.filename
            file_id = generate_unique_id_mst()
            file_path = os.path.join(UPLOAD_FOLDER_NOTES, subject, f'{file_id}_{filename}')
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)

            file_hash = calculate_file_hash_mst(file_path)
            upload_date = datetime.now().strftime('%d-%m-%y')

            conn = sqlite3.connect('database/Notes.db')
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM notes WHERE file_hash=? AND subject=?', (file_hash, subject))
            existing_file = cursor.fetchone()

            if existing_file:
                os.remove(file_path)
                conn.close()
                return jsonify({'success': False, 'message': 'File already exists'})

            cursor.execute('INSERT INTO notes (file_id, filename, file_path, file_hash, subject, upload_date) VALUES (?, ?, ?, ?, ?, ?)',
                           (file_id, filename, file_path, file_hash, subject, upload_date))
            conn.commit()
            conn.close()

            uploaded_files.append(filename)
        else:
            return jsonify({'success': False, 'message': f'File type not allowed: {file.filename}'})

    return jsonify({'success': True, 'message': 'Files uploaded successfully', 'uploaded_files': uploaded_files})

@routes_bp.route('/get_uploaded_notes', methods=['GET'])
def get_uploaded_notes():
    subject = request.args.get('subject')
    if not subject:
        return jsonify({'success': False, 'message': 'Subject not provided'})

    conn = sqlite3.connect('database/Notes.db')
    cursor = conn.cursor()

    cursor.execute('SELECT file_id, filename, file_path, upload_date FROM notes WHERE subject=?', (subject,))
    notes = [{'id': row[0], 'filename': row[1], 'filepath': row[2], 'upload_date': row[3]} for row in cursor.fetchall()]

    conn.close()

    return jsonify({'success': True, 'notes': notes})


@routes_bp.route('/remove_note', methods=['POST'])
def remove_note():
    data = request.get_json()
    file_id = data.get('file_id')
    file_path = data.get('file_path')
    subject = data.get('subject')

    if not file_id or not file_path or not subject:
        return jsonify({'success': False, 'message': 'Invalid request'})

    try:
        if os.path.exists(file_path):
            os.remove(file_path)

        conn = sqlite3.connect('database/Notes.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM notes WHERE file_id=? AND subject=?', (file_id, subject))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'File removed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    
######################################## Route for Notes Uploading END ########################################


######################################## Route for MST Papers Uploading START ########################################

UPLOAD_FOLDER_MST = os.path.join(os.getcwd(), 'static', 'Assets', 'MST Papers')
ALLOWED_MST = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'ppt', 'pptx', 'doc', 'docx', 'xls', 'xlsx', 'webp'}

def generate_unique_id_mst():
    return str(uuid.uuid4().hex[:4])

def calculate_file_hash_mst(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def allowed_file_mst(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_MST

@routes_bp.route('/upload_mst_paper', methods=['POST'])
def upload_mst_paper():
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'})

    files = request.files.getlist('files')
    subject = request.form.get('subject')

    uploaded_files = []
    for file in files:
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No selected file'})

        if file and allowed_file_mst(file.filename):
            filename = file.filename
            file_id = generate_unique_id_mst()
            file_path = os.path.join(UPLOAD_FOLDER_MST, subject, f'{file_id}_{filename}')
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)

            file_hash = calculate_file_hash_mst(file_path)
            upload_date = datetime.now().strftime('%d-%m-%y')

            conn = sqlite3.connect('database/MSTPapers.db')
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM mst_papers WHERE file_hash=? AND subject=?', (file_hash, subject))
            existing_file = cursor.fetchone()

            if existing_file:
                os.remove(file_path)
                conn.close()
                return jsonify({'success': False, 'message': 'File already exists'})

            cursor.execute('INSERT INTO mst_papers (file_id, filename, file_path, file_hash, subject, upload_date) VALUES (?, ?, ?, ?, ?, ?)',
                           (file_id, filename, file_path, file_hash, subject, upload_date))
            conn.commit()
            conn.close()

            uploaded_files.append(filename)
        else:
            return jsonify({'success': False, 'message': f'File type not allowed: {file.filename}'})

    return jsonify({'success': True, 'message': 'Files uploaded successfully', 'uploaded_files': uploaded_files})

@routes_bp.route('/get_uploaded_mst_paper', methods=['GET'])
def get_uploaded_mst_paper():
    subject = request.args.get('subject')
    if not subject:
        return jsonify({'success': False, 'message': 'Subject not provided'})

    conn = sqlite3.connect('database/MSTPapers.db')
    cursor = conn.cursor()

    cursor.execute('SELECT file_id, filename, file_path, upload_date FROM mst_papers WHERE subject=?', (subject,))
    mstPapers = [{'id': row[0], 'filename': row[1], 'filepath': row[2], 'upload_date': row[3]} for row in cursor.fetchall()]

    conn.close()

    return jsonify({'success': True, 'mstPapers': mstPapers})


@routes_bp.route('/remove_mst_paper', methods=['POST'])
def remove_mst_paper():
    data = request.get_json()
    file_id = data.get('file_id')
    file_path = data.get('file_path')
    subject = data.get('subject')

    if not file_id or not file_path or not subject:
        return jsonify({'success': False, 'message': 'Invalid request'})

    try:
        if os.path.exists(file_path):
            os.remove(file_path)

        conn = sqlite3.connect('database/MSTPapers.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM mst_papers WHERE file_id=? AND subject=?', (file_id, subject))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'File removed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    
######################################## Route for MST Papers Uploading END ########################################

######################################## Route for MST Papers Uploading START ########################################

UPLOAD_FOLDER_PREVIOUS = os.path.join(os.getcwd(), 'static', 'Assets', 'PreviousPapers')
ALLOWED_PREVIOUS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'ppt', 'pptx', 'doc', 'docx', 'xls', 'xlsx',}

def generate_unique_id_paper():
    return str(uuid.uuid4().hex[:4])

def calculate_file_hash_paper(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def allowed_file_paper(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PREVIOUS

@routes_bp.route('/upload_previous_paper', methods=['POST'])
def upload_previous_paper():
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'})

    files = request.files.getlist('files')
    subject = request.form.get('subject')

    uploaded_files = []
    for file in files:
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No selected file'})

        if file and allowed_file_paper(file.filename):
            filename = file.filename
            file_id = generate_unique_id_paper()
            file_path = os.path.join(UPLOAD_FOLDER_PREVIOUS, subject, f'{file_id}_{filename}')
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)

            file_hash = calculate_file_hash_paper(file_path)
            upload_date = datetime.now().strftime('%d-%m-%y')

            conn = sqlite3.connect('database/PreviousPapers.db')
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM previous_papers WHERE file_hash=? AND subject=?', (file_hash, subject))
            existing_file = cursor.fetchone()

            if existing_file:
                os.remove(file_path)
                conn.close()
                return jsonify({'success': False, 'message': 'File already exists'})

            cursor.execute('INSERT INTO previous_papers (file_id, filename, file_path, file_hash, subject, upload_date) VALUES (?, ?, ?, ?, ?, ?)',
                           (file_id, filename, file_path, file_hash, subject, upload_date))
            conn.commit()
            conn.close()

            uploaded_files.append(filename)
        else:
            return jsonify({'success': False, 'message': f'File type not allowed: {file.filename}'})

    return jsonify({'success': True, 'message': 'Files uploaded successfully', 'uploaded_files': uploaded_files})

@routes_bp.route('/get_uploaded_previous_paper', methods=['GET'])
def get_uploaded_previous_paper():
    subject = request.args.get('subject')
    if not subject:
        return jsonify({'success': False, 'message': 'Subject not provided'})

    conn = sqlite3.connect('database/PreviousPapers.db')
    cursor = conn.cursor()

    cursor.execute('SELECT file_id, filename, file_path, upload_date FROM previous_papers WHERE subject=?', (subject,))
    PreviousPapers = [{'id': row[0], 'filename': row[1], 'filepath': row[2], 'upload_date': row[3]} for row in cursor.fetchall()]

    conn.close()

    return jsonify({'success': True, 'PreviousPapers': PreviousPapers})


@routes_bp.route('/remove_previous_paper', methods=['POST'])
def remove_previous_paper():
    data = request.get_json()
    file_id = data.get('file_id')
    file_path = data.get('file_path')
    subject = data.get('subject')

    if not file_id or not file_path or not subject:
        return jsonify({'success': False, 'message': 'Invalid request'})

    try:
        if os.path.exists(file_path):
            os.remove(file_path)

        conn = sqlite3.connect('database/PreviousPapers.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM previous_papers WHERE file_id=? AND subject=?', (file_id, subject))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'File removed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    
######################################## Route for MST Papers Uploading END ########################################
    

@routes_bp.route('/make_announcement', methods=['POST'])
def make_announcement():
    try:
        title = request.form['title']
        organising_club = request.form['organising_club']
        registration_link = request.form['registration_link']
        event_date = request.form['event_date']
        description = request.form['description']
        banner = request.files['banner']
        fname = request.form['fname']
        lname = request.form['lname']
        userid = request.form['userid']

        if banner and allowed_file(banner.filename):
            filename = str(uuid.uuid4()) + '_' + secure_filename(banner.filename)
            banner_path = os.path.join('static/Assets/Announcement', filename)
            banner.save(banner_path)

            conn = sqlite3.connect('database/Announcement.db')
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS announcements (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    organising_club TEXT,
                    registration_link TEXT,
                    event_date TEXT,
                    banner_path TEXT,
                    description TEXT,
                    fname TEXT,
                    lname TEXT,
                    userid TEXT
                )
            ''')

            announcement_id = generate_unique_id(cursor)

            cursor.execute('''
                INSERT INTO announcements (id, title, organising_club, registration_link, event_date, banner_path, description, fname, lname, userid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (announcement_id, title, organising_club, registration_link, event_date, banner_path, description, fname, lname, userid))

            conn.commit()
            conn.close()

            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Invalid file type or size exceeds limit.'})

    except Exception as e:
        print(f"Error making announcement: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while making the announcement.'})

@routes_bp.route('/get_uploaded_announcements', methods=['GET'])
def get_uploaded_announcements():
    try:
        conn = sqlite3.connect('database/Announcement.db')
        cursor = conn.cursor()

        cursor.execute('SELECT id, title, organising_club, event_date, banner_path, description, fname, lname, userid, registration_link FROM announcements')
        announcements = [
            {'id': row[0], 'title': row[1], 'organising_club': row[2], 'event_date': row[3], 'banner_path': row[4], 'description': row[5], 'fname': row[6], 'lname': row[7], 'userid': row[8], 'registration_link': row[9]}
            for row in cursor.fetchall()
        ]

        conn.close()

        return jsonify({'success': True, 'announcements': announcements})

    except Exception as e:
        print(f"Error getting uploaded announcements: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while getting uploaded announcements.'})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def generate_unique_id(cursor):
    while True:
        unique_id = str(uuid.uuid4())
        cursor.execute('SELECT id FROM announcements WHERE id = ?', (unique_id,))
        if cursor.fetchone() is None:
            return unique_id

def delete_old_announcements():
    try:
        conn = sqlite3.connect('database/Announcement.db')
        cursor = conn.cursor()

        cursor.execute('SELECT id, banner_path, event_date FROM announcements')
        announcements = cursor.fetchall()

        current_date = datetime.now()

        for id, banner_path, event_date_str in announcements:
            event_date = datetime.strptime(event_date_str, '%d-%m-%y')
            deletion_date = event_date + timedelta(days=7)

            if current_date >= deletion_date:
                cursor.execute('DELETE FROM announcements WHERE id = ?', (id,))
                conn.commit()

                if os.path.exists(banner_path):
                    os.remove(banner_path)

                print(f"Deleted announcement {id} and its banner.")

        conn.close()

    except Exception as e:
        print(f"Error deleting old announcements: {str(e)}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(delete_old_announcements, CronTrigger(hour=0, minute=0))
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

start_scheduler()