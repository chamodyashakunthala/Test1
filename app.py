from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import json
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")
app = Flask(__name__)
CORS(app)

# In-memory storage (replace with database in production)
doctors = []
rooms = []
availability_slots = []
appointments = []

# Helper function to check time overlap
def check_overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

# Generate unique IDs
def get_next_id(collection):
    return max([item['id'] for item in collection], default=0) + 1

# DOCTOR ENDPOINTS
@app.route('/api/doctors', methods=['GET'])
def get_doctors():
    return jsonify(doctors)

@app.route('/api/doctors', methods=['POST'])
def add_doctor():
    data = request.json
    doctor = {
        'id': get_next_id(doctors),
        'name': data['name'],
        'specialization': data['specialization'],
        'phone': data.get('phone', '')
    }
    doctors.append(doctor)
    return jsonify(doctor), 201

@app.route('/api/doctors/<int:doctor_id>', methods=['DELETE'])
def delete_doctor(doctor_id):
    global doctors
    doctors = [d for d in doctors if d['id'] != doctor_id]
    return jsonify({'message': 'Doctor deleted'}), 200

# ROOM ENDPOINTS
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    return jsonify(rooms)

@app.route('/api/rooms', methods=['POST'])
def add_room():
    data = request.json
    room = {
        'id': get_next_id(rooms),
        'number': data['number'],
        'type': data['type'],
        'capacity': data.get('capacity', 1)
    }
    rooms.append(room)
    return jsonify(room), 201

@app.route('/api/rooms/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    global rooms
    rooms = [r for r in rooms if r['id'] != room_id]
    return jsonify({'message': 'Room deleted'}), 200

# AVAILABILITY ENDPOINTS
@app.route('/api/availability', methods=['GET'])
def get_availability():
    doctor_id = request.args.get('doctor_id', type=int)
    date = request.args.get('date')
    
    filtered = availability_slots
    if doctor_id:
        filtered = [a for a in filtered if a['doctor_id'] == doctor_id]
    if date:
        filtered = [a for a in filtered if a['date'] == date]
    
    return jsonify(filtered)

@app.route('/api/availability', methods=['POST'])
def add_availability():
    data = request.json
    slot = {
        'id': get_next_id(availability_slots),
        'doctor_id': data['doctor_id'],
        'date': data['date'],
        'start_time': data['start_time'],
        'end_time': data['end_time']
    }
    availability_slots.append(slot)
    return jsonify(slot), 201

@app.route('/api/availability/<int:slot_id>', methods=['DELETE'])
def delete_availability(slot_id):
    global availability_slots
    availability_slots = [a for a in availability_slots if a['id'] != slot_id]
    return jsonify({'message': 'Availability deleted'}), 200

# APPOINTMENT ENDPOINTS
@app.route('/api/appointments', methods=['GET'])
def get_appointments():
    date = request.args.get('date')
    
    if date:
        filtered = [a for a in appointments if a['date'] == date]
        return jsonify(filtered)
    
    return jsonify(appointments)

@app.route('/api/appointments', methods=['POST'])
def create_appointment():
    data = request.json
    
    # Check doctor availability
    doctor_available = False
    for slot in availability_slots:
        if (slot['doctor_id'] == data['doctor_id'] and 
            slot['date'] == data['date'] and
            slot['start_time'] <= data['start_time'] and
            slot['end_time'] >= data['end_time']):
            doctor_available = True
            break
    
    if not doctor_available:
        return jsonify({'error': 'Doctor not available at this time'}), 400
    
    # Check for double booking - doctor
    for apt in appointments:
        if (apt['doctor_id'] == data['doctor_id'] and 
            apt['date'] == data['date'] and
            check_overlap(apt['start_time'], apt['end_time'], 
                         data['start_time'], data['end_time'])):
            return jsonify({'error': 'Doctor already has an appointment at this time'}), 400
    
    # Check for double booking - room
    for apt in appointments:
        if (apt['room_id'] == data['room_id'] and 
            apt['date'] == data['date'] and
            check_overlap(apt['start_time'], apt['end_time'], 
                         data['start_time'], data['end_time'])):
            return jsonify({'error': 'Room already booked at this time'}), 400
    
    appointment = {
        'id': get_next_id(appointments),
        'patient_name': data['patient_name'],
        'patient_phone': data.get('patient_phone', ''),
        'doctor_id': data['doctor_id'],
        'room_id': data['room_id'],
        'date': data['date'],
        'start_time': data['start_time'],
        'end_time': data['end_time'],
        'notes': data.get('notes', '')
    }
    
    appointments.append(appointment)
    return jsonify(appointment), 201

@app.route('/api/appointments/<int:apt_id>', methods=['DELETE'])
def delete_appointment(apt_id):
    global appointments
    appointments = [a for a in appointments if a['id'] != apt_id]
    return jsonify({'message': 'Appointment deleted'}), 200

# Dashboard endpoint - today's schedule
@app.route('/api/dashboard/today', methods=['GET'])
def get_today_schedule():
    today = datetime.now().strftime('%Y-%m-%d')
    today_appointments = [a for a in appointments if a['date'] == today]
    
    # Enrich with doctor and room info
    enriched = []
    for apt in today_appointments:
        doctor = next((d for d in doctors if d['id'] == apt['doctor_id']), None)
        room = next((r for r in rooms if r['id'] == apt['room_id']), None)
        
        enriched.append({
            **apt,
            'doctor_name': doctor['name'] if doctor else 'Unknown',
            'doctor_specialization': doctor['specialization'] if doctor else '',
            'room_number': room['number'] if room else 'Unknown'
        })
    
    return jsonify({
        'date': today,
        'appointments': sorted(enriched, key=lambda x: x['start_time'])
    })

if __name__ == '__main__':

    app.run(debug=True, port=5000)
