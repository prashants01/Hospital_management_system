from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Replace with a secure secret key

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="",  # Replace with your MySQL username
        password="",  # Replace with your MySQL password
        database="hospital"  # Replace with your database name
    )

# Function to send email
def send_email(receiver, subject, body):
    sender = ""  # Your Gmail address
    sender_password = ""  # Gmail App Password
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, sender_password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Routes

@app.route("/")
def home():
    if "user_id" in session:
        return render_template("index.html")
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")
        flash("Invalid username or password.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)
        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            connection.commit()
            flash("Registration successful. Please log in.")
            return redirect("/login")
        except mysql.connector.IntegrityError:
            flash("Username already exists.")
        finally:
            cursor.close()
            connection.close()
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/patients", methods=["GET", "POST"])
def patients():
    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        age = request.form["age"]
        diagnosis = request.form["diagnosis"]
        email = request.form["email"]
        gender = request.form["gender"]
        appointment_time = request.form["appointment_time"]
        contact_no = request.form["contact_no"]
        blood_group = request.form["blood_group"]

        # Generate OTP and send email
        otp = random.randint(100000, 999999)
        session["otp"] = otp
        session["patient_data"] = {
            "name": name,
            "age": age,
            "diagnosis": diagnosis,
            "email": email,
            "gender": gender,
            "appointment_time": appointment_time,
            "contact_no": contact_no,
            "blood_group": blood_group,
        }

        subject = "OTP Verification for Patient Registration"
        body = f"Your OTP for registration is: {otp}. Please use this to complete your registration."
        send_email(email, subject, body)

        flash("An OTP has been sent to the provided email. Please verify.")
        return redirect("/patients/verify-otp")

    cursor.execute("SELECT * FROM patients")
    patients = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template("patients.html", patients=patients)

@app.route("/patients/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if "otp" not in session or "patient_data" not in session:
        return redirect("/patients")

    if request.method == "POST":
        entered_otp = request.form["otp"]
        if int(entered_otp) == session["otp"]:
            # Add patient to the database
            patient_data = session["patient_data"]
            connection = get_db_connection()
            cursor = connection.cursor()
            query = """
                INSERT INTO patients (name, age, diagnosis, email, gender, appointment_time, contact_no, blood_group)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                patient_data["name"],
                patient_data["age"],
                patient_data["diagnosis"],
                patient_data["email"],
                patient_data["gender"],
                patient_data["appointment_time"],
                patient_data["contact_no"],
                patient_data["blood_group"],
            ))
            connection.commit()
            cursor.close()
            connection.close()

            # Send confirmation email
            subject = "Registration Successful"
            body = f"Dear {patient_data['name']},\n\nYour registration was successful.\n\nThank you for choosing our hospital!"
            send_email(patient_data["email"], subject, body)

            # Clear session data
            session.pop("otp", None)
            session.pop("patient_data", None)

            flash("Patient registration successful. Confirmation email sent.")
            return redirect("/patients")
        else:
            flash("Invalid OTP. Please try again.")

    return render_template("verify_otp.html")

@app.route("/patients/delete/<int:id>")
def delete_patient(id):
    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM patients WHERE id = %s", (id,))
    connection.commit()
    cursor.close()
    connection.close()
    flash("Patient deleted successfully.")
    return redirect("/patients")

@app.route("/doctors", methods=["GET", "POST"])
def doctors():
    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        specialization = request.form["specialization"]
        experience = request.form["experience"]
        gender = request.form["gender"]

        query = """
            INSERT INTO doctors (name, specialization, experience, gender)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (name, specialization, experience, gender))
        connection.commit()
        flash("Doctor added successfully.")
        return redirect("/doctors")

    cursor.execute("SELECT * FROM doctors")
    doctors = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template("doctors.html", doctors=doctors)

@app.route("/doctors/delete/<int:id>")
def delete_doctor(id):
    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM doctors WHERE id = %s", (id,))
    connection.commit()
    cursor.close()
    connection.close()
    flash("Doctor deleted successfully.")
    return redirect("/doctors")

# Run the application
if __name__ == "__main__":
    app.run(debug=True)
