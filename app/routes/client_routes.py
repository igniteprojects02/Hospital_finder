from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Client, Hospital,Doctor, Appointment,MedicalHistory,Review
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user,login_required, current_user, logout_user

bp= Blueprint('client_routes', __name__)

# Client Sign-Up Route
from flask import render_template

@bp.route('/signup', methods=['GET', 'POST'])
def client_signup():
    if request.method == 'POST':
        data = request.get_json()
        
        # Validate the incoming data
        if not data.get('email') or not data.get('username') or not data.get('password') or not data.get('name') or not data.get('age') or not data.get('address'):
            return jsonify({"message": "Missing required fields"}), 400

        # Check if the user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({"message": "User already exists"}), 409

        # Create a new User (client) object
        hashed_password = generate_password_hash(data['password'])
        new_user = User(
            username=data['username'],
            email=data['email'],
            password=hashed_password,
            role='client'  # Set role as 'client'
        )

        db.session.add(new_user)
        db.session.commit()

        # Create the associated Client record
        new_client = Client(
            name=data['name'],
            age=data['age'],
            address=data['address'],
            user_id=new_user.id  # Link Client to User
        )

        db.session.add(new_client)
        db.session.commit()

        return jsonify({
            "message": "Client registered successfully",
            "client": {
                "username": new_user.username,
                "email": new_user.email,
                "name": new_client.name,
                "age": new_client.age,
                "address": new_client.address
            }
        }), 201
    
    # Render the signup page (GET request)
    return render_template('client/signup.html')

# Client Login Route (Updated to use username instead of email)
@bp.route('/login', methods=['GET', 'POST'])
def client_login():
    if request.method == 'POST':
        data = request.get_json()

        # Validate the incoming data
        if not data.get('username') or not data.get('password'):
            return jsonify({"message": "Missing required fields"}), 400

        # Find the user by username
        user = User.query.filter_by(username=data['username']).first()
        if not user:
            return jsonify({"message": "Invalid credentials"}), 401

        # Check if the password is correct
        if not check_password_hash(user.password, data['password']):
            return jsonify({"message": "Invalid credentials"}), 401

        # Log the user in using Flask-Login
        login_user(user)

        return jsonify({
            "message": "Login successful",
            "user": {
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }), 200
    
    # Render the login page (GET request)
    return render_template('client/login.html')
@bp.route('/dashboard', methods=['GET'])
@login_required
def client_dashboard():
    return render_template('client/dashboard.html')

from flask import render_template

from sqlalchemy import func

from jinja2 import Template

@bp.route('/hospitals/search', methods=['GET'])
@login_required
def search_hospitals():
    place = request.args.get('place', default=None, type=str)
    pin_code = request.args.get('pin_code', default=None, type=str)
    sort_by = request.args.get('sort_by', default=None, type=str)  # Get the sorting option
    review_keyword = request.args.get('review_keyword', default=None, type=str)  # New parameter for review search

    # Query only approved hospitals based on the provided search criteria
    query = db.session.query(Hospital).filter(Hospital.is_approved == True)
    
    if place:
        query = query.filter(Hospital.address.ilike(f'%{place}%'))  # Case-insensitive search
    if pin_code:
        query = query.filter(Hospital.pin_code == pin_code)
    
    # Filter hospitals based on review keyword
    if review_keyword:
        query = query.join(Review).filter(Review.review_text.ilike(f'%{review_keyword}%'))

    # Sorting logic based on the selected option
    if sort_by == 'rating_desc':
        # Sort by average rating, highest first
        query = query.join(Review).group_by(Hospital.id).having(db.func.avg(Review.rating).isnot(None)).order_by(db.func.avg(Review.rating).desc())
    elif sort_by == 'rating_asc':
        # Sort by average rating, lowest first
        query = query.join(Review).group_by(Hospital.id).having(db.func.avg(Review.rating).isnot(None)).order_by(db.func.avg(Review.rating).asc())

    hospitals = query.all()

    # Calculate average rating for each hospital
    hospitals_with_ratings = []
    for hospital in hospitals:
        reviews = Review.query.filter_by(hospital_id=hospital.id).all()
        if reviews:
            average_rating = sum(review.rating for review in reviews) / len(reviews)
        else:
            average_rating = 0  # No reviews, set to 0
        hospitals_with_ratings.append((hospital, int(round(average_rating, 1))))  # Round to 1 decimal place

    return render_template('client/hospital-search.html', hospitals=hospitals_with_ratings, int=int)

@bp.route('/hospitals/<int:hospital_id>', methods=['GET'])
@login_required
def get_hospital_details(hospital_id):
    # Retrieve the hospital from the database by ID
    hospital = Hospital.query.get(hospital_id)
    
    if hospital is None:
        return render_template('client/hospital-search.html', error="Hospital not found")
    
    # Get the list of doctors for the hospital
    doctors = hospital.doctors  # Assuming you have a relationship defined as `doctors` in the Hospital model

    # Compute the average rating for the hospital
    from sqlalchemy.sql import func
    average_rating = db.session.query(func.avg(Review.rating)).filter_by(hospital_id=hospital_id).scalar()
    average_rating = round(average_rating) if average_rating else 0  # Default to 0 if no ratings

    return render_template(
        'client/hospital.html',
        hospital=hospital,
        doctors=doctors,
        average_rating=average_rating
    )
@bp.route('/hospital/<int:hospital_id>/doctors', methods=['GET'])
@login_required
def get_doctors_in_hospital(hospital_id):
    # Retrieve the hospital from the database
    hospital = Hospital.query.get(hospital_id)
    
    if hospital is None:
        # Render an error page or redirect with an error message
        return render_template('error.html', message="Hospital not found"), 404
    
    # Query the doctors for the specified hospital
    doctors = hospital.doctors  # Assuming you have a relationship defined as `doctors` in Hospital model
    
    # Render the doctors.html template with the hospital and doctors data
    return render_template('client/doctors.html', hospital=hospital, doctors=doctors)

@bp.route('/appointments/book/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def book_appointment(doctor_id):
    """
    Handles appointment booking for a specific doctor.
    """
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        return jsonify({"message": "Doctor not found"}), 404

    if request.method == 'GET':
        # Retrieve the client's existing appointments with this doctor
        appointments = Appointment.query.filter_by(doctor_id=doctor_id, client_id=current_user.id).all()
        
        # Render the booking page with doctor details and existing appointments
        return render_template('client/booking.html', doctor=doctor, appointments=appointments)

    elif request.method == 'POST':
        appointment_time = request.form.get('appointment_time')

        if not appointment_time:
            return jsonify({"message": "Missing required fields"}), 400

        # Ensure only clients can book
        if current_user.role != 'client':
            return jsonify({"message": "Only clients can book appointments"}), 403

        # Create the appointment
        appointment = Appointment(
            appointment_time=appointment_time,
            status="Pending",
            doctor_id=doctor.id,
            client_id=current_user.id
        )

        try:
            db.session.add(appointment)
            db.session.commit()
            # Retrieve updated list of appointments after booking
            appointments = Appointment.query.filter_by(doctor_id=doctor_id, client_id=current_user.id).all()
            return render_template('client/booking.html', doctor=doctor, success_message="Appointment booked successfully", appointments=appointments)
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": "Failed to book appointment", "error": str(e)}), 500
@bp.route('/appointments/cancel/<int:appointment_id>', methods=['GET'])
@login_required
def cancel_appointment(appointment_id):
    """
    Handles the cancellation of a client's appointment.
    """
    # Retrieve the appointment to be canceled
    appointment = Appointment.query.get(appointment_id)

    if not appointment:
        return jsonify({"message": "Appointment not found"}), 404

    # Check if the current user is the one who booked the appointment
    if appointment.client_id != current_user.id:
        return jsonify({"message": "You are not authorized to cancel this appointment"}), 403

    try:
        # Delete the appointment
        db.session.delete(appointment)
        db.session.commit()
        
        # Redirect back to the doctor's booking page with a success message
        return redirect(url_for('client_routes.book_appointment', doctor_id=appointment.doctor_id, success_message="Appointment canceled successfully"))
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to cancel appointment", "error": str(e)}), 500
@bp.route('/medical-history', methods=['GET'])
@login_required
def get_current_user_medical_history():
    """
    Retrieves and displays the medical history of the logged-in client.
    """
    # Check if the logged-in user is a client
    if current_user.role != 'client':
        return jsonify({"message": "Access denied. Only clients can view medical history."}), 403

    # Retrieve the medical history for the logged-in client
    medical_histories = MedicalHistory.query.filter_by(client_id=current_user.id).all()

    if not medical_histories:
        return render_template('client/medical_history.html', message="No medical history found.")

    # Format the medical history for the template, including the hospital name and doctor's name
    history_list = []
    for history in medical_histories:
        hospital = Hospital.query.get(history.hospital_id)
        doctor = Doctor.query.get(history.doctor_id)  # Assuming there is a doctor_id field in the MedicalHistory model
        history_list.append({
            "id": history.id,
            "medical_note": history.medical_note,
            "timestamp": history.timestamp.isoformat(),
            "hospital_name": hospital.name if hospital else "Unknown",
            "doctor_name": doctor.name if doctor else "Unknown Doctor",  # Add the doctor's name
        })

    return render_template('client/medical_history.html', medical_histories=history_list)


@bp.route('/profile', methods=['GET'])
@login_required
def client_profile():
    profile = {
        "username": current_user.username,
        "email": current_user.email,
        "client_info": {
            "name": current_user.client_info.name if current_user.client_info else None,
            "age": current_user.client_info.age if current_user.client_info else None,
            "address": current_user.client_info.address if current_user.client_info else None
        }
    }
    return render_template('client/profile.html', profile=profile)
from flask import flash, redirect, url_for

@bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def client_edit_profile():
    if request.method == 'POST':
        data = request.form

        # Update the User model
        if "username" in data:
            current_user.username = data["username"]

        if "email" in data:
            current_user.email = data["email"]

        # Update Client Info (if the user is a client)
        if current_user.role == 'client' and current_user.client_info:
            client_info = current_user.client_info

            if "name" in data:
                client_info.name = data["name"]

            if "age" in data:
                client_info.age = int(data["age"]) if data["age"].isdigit() else None

            if "address" in data:
                client_info.address = data["address"]

        # Commit changes to the database
        db.session.commit()

        # Flash a success message
        flash("Your profile has been updated successfully!", "success")
        return redirect(url_for('client_routes.client_profile'))  # Redirect to profile page

    # Render edit profile page
    profile = {
        "username": current_user.username,
        "email": current_user.email,
        "client_info": {
            "name": current_user.client_info.name if current_user.client_info else None,
            "age": current_user.client_info.age if current_user.client_info else None,
            "address": current_user.client_info.address if current_user.client_info else None
        }
    }
    return render_template('client/edit-profile.html', profile=profile)

from flask import request, jsonify
import google.generativeai as genai

# Configure the API key
genai.configure(api_key="AIzaSyAqG82KPp49bu-zd2hg_Ss5Glf0wi1PCHY")
model = genai.GenerativeModel("gemini-1.5-flash")

@bp.route('/chatbot', methods=['POST'])
@login_required
def chatbot_response():
    data = request.get_json()
    symptom = data.get('symptom')

    # Generate response from Gemini
    gemini_response = model.generate_content(f"consider yourself as a medical professional. I am going to give you a Symptom, simply answer which doctor to consult and what might be the potential disease or diagnose. answer in just 2 t0 5 scentence. SYmpton: {symptom}. What could it be? Provide advice.")
    response_message = gemini_response.text

    # You can add logic here to link hospitals based on the symptom
    hospital_link = "/client/hospitals/search"

    return jsonify({
        'message': response_message,
        'hospital_link': hospital_link
    })


from flask import redirect, url_for

@bp.route('/logout', methods=['GET','POST'])
@login_required
def client_logout():
    if current_user.role != 'client':
        return jsonify({"message": "Unauthorized access."}), 403
    
    # Log out the user (invalidate the session)
    logout_user()

    # Redirect to the login page after logout
    return redirect('/client/login')  # Adjust 'auth.login' to match the actual blueprint and route name for login

@bp.route('/hospital/<int:hospital_id>/reviews/add', methods=['POST'])
@login_required
def add_hospital_review(hospital_id):
    if current_user.role != 'client':
        return redirect('/login')

    rating = int(request.form['rating'])
    review_text = request.form['review_text']

    if not (1 <= rating <= 5):
        flash('Rating must be between 1 and 5.')
        return redirect(f'/hospital/{hospital_id}/reviews')

    review = Review(rating=rating, review_text=review_text, client_id=current_user.id, hospital_id=hospital_id)
    db.session.add(review)
    db.session.commit()

    flash('Review submitted successfully!')
    return redirect(f'/client/hospital/{hospital_id}/reviews')
@bp.route('/hospital/<int:hospital_id>/reviews', methods=['GET'])
@login_required
def view_hospital_reviews(hospital_id):
    hospital = Hospital.query.get_or_404(hospital_id)

    # Fetch reviews for the hospital
    reviews = Review.query.filter_by(hospital_id=hospital_id).order_by(Review.timestamp.desc()).all()

    # Pass the reviews and hospital information to the template
    return render_template('client/hospital_reviews.html', hospital=hospital, reviews=reviews)



from io import BytesIO
from flask import send_file
from fpdf import FPDF

@bp.route('/download-medical-history-pdf', methods=['GET'])
@login_required
def download_medical_history_pdf():
    """
    Allows the logged-in client to download their medical history as a PDF.
    """
    # Check if the logged-in user is a client
    if current_user.role != 'client':
        return jsonify({"message": "Access denied. Only clients can download medical history."}), 403

    # Retrieve the medical history for the logged-in client
    medical_histories = MedicalHistory.query.filter_by(client_id=current_user.id).all()

    if not medical_histories:
        return jsonify({"message": "No medical history found."}), 404

    # Prepare the content for the PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(200, 10, txt="Medical History Report", ln=True, align='C')

    pdf.set_font('Arial', '', 12)

    # Iterate through the medical history records
    for history in medical_histories:
        # Retrieve hospital and doctor data
        hospital = history.hospital  # Access the Hospital object related to the MedicalHistory
        hospital_name = hospital.name if hospital else "Unknown Hospital"

        doctor = Doctor.query.get(history.doctor_id)  # Assuming doctor_id exists in MedicalHistory
        doctor_name = doctor.name if doctor else "Unknown Doctor"

        # Add the details to the PDF
        pdf.ln(10)
        pdf.cell(200, 10, f"Hospital: {hospital_name}", ln=True)
        pdf.cell(200, 10, f"Doctor: {doctor_name}", ln=True)
        pdf.cell(200, 10, f"Medical Note: {history.medical_note}", ln=True)
        pdf.cell(200, 10, f"Timestamp: {history.timestamp}", ln=True)

    # Save the PDF to a string (using 'S' option in output)
    pdf_output = pdf.output(dest='S').encode('latin1')  # Get PDF as bytes in memory

    # Convert the output to a BytesIO object
    pdf_stream = BytesIO(pdf_output)

    # Rewind the BytesIO object before sending it
    pdf_stream.seek(0)

    # Return the PDF as a downloadable file
    return send_file(pdf_stream, as_attachment=True, download_name="medical_history.pdf", mimetype="application/pdf")
