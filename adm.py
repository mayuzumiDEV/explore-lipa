from flask import Flask, render_template, Blueprint, request, jsonify
from mysql.connector import Error
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def create_connection():
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',
            user='root',
            password='',  
            database='lipacitytourism'
        )
        if connection.is_connected():
            print("Successfully connected to the database")
        return connection
    except Error as e:
        print(f"Error: '{e}'")
        return None

adm = Blueprint('adm', __name__, template_folder='admin')

@adm.route('/dashboard')
def dashboard():
    conn = create_connection()
    cursor = conn.cursor()

    user_profile_query = "SELECT userID, adventurerID, gender, contact_number, address, age FROM userprofile"
    cursor.execute(user_profile_query)
    user_profiles = cursor.fetchall()

    address_data = {'residents': 0, 'visitors': 0}
    for _, _, _, _, address, _ in user_profiles:
        if 'lipa' in address.lower():  
            address_data['residents'] += 1
        else:
            address_data['visitors'] += 1

    gender_query = """
    SELECT LOWER(gender) as gender, COUNT(*) 
    FROM userprofile 
    GROUP BY gender
    """
    cursor.execute(gender_query)
    gender_counts = cursor.fetchall()

    gender_data = {'male': 0, 'female': 0, 'others': 0, 'prefer not': 0}
    for gender, count in gender_counts:
        if gender in gender_data:
            gender_data[gender] = count
        else:
            gender_data['others'] += count

    feedback_query = """
        SELECT MONTH(created_at) AS month, COUNT(DISTINCT name) AS visitor_count
        FROM ratings
        GROUP BY month
        ORDER BY month;
    """
    cursor.execute(feedback_query)
    feedbacks = cursor.fetchall()

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_visitors = [0] * 12  

    for feedback in feedbacks:
        month_index = feedback[0] - 1
        visitor_count = feedback[1]
        monthly_visitors[month_index] = visitor_count
            
    '''review_query = "SELECT id, name, created_at, place, star_rate FROM ratings"
    cursor.execute(review_query)
    reviews = cursor.fetchall()'''

    recommendation_query = "SELECT COUNT(recommendation) FROM ratings WHERE recommendation IS NOT NULL AND recommendation != ''"
    cursor.execute(recommendation_query)
    total_recommendations = cursor.fetchone()[0]  
    
    comment_query = "SELECT COUNT(comment) FROM ratings WHERE comment IS NOT NULL AND comment != ''"
    cursor.execute(comment_query)
    total_comments = cursor.fetchone()[0]

    login_query = "SELECT COUNT(*) FROM login"
    cursor.execute(login_query)
    total_logins = cursor.fetchone()[0]

    star_counts = {}
    for i in range(1, 6):
        cursor.execute(f"SELECT COUNT(*) FROM ratings WHERE star_rate = {i}")
        star_counts[f"{i}_star"] = cursor.fetchone()[0]

    place_query = """
    SELECT place, COUNT(*) as visit_count
    FROM ratings
    GROUP BY place
    ORDER BY visit_count DESC
    LIMIT 10;
    """
    cursor.execute(place_query)
    places = cursor.fetchall()
    
    selected_rating = request.args.get('star_rate', 'all')

    rating_query = """
        SELECT place, 
            SUM(CASE WHEN star_rate = 1 THEN 1 ELSE 0 END) AS one_star,
            SUM(CASE WHEN star_rate = 2 THEN 1 ELSE 0 END) AS two_star,
            SUM(CASE WHEN star_rate = 3 THEN 1 ELSE 0 END) AS three_star,
            SUM(CASE WHEN star_rate = 4 THEN 1 ELSE 0 END) AS four_star,
            SUM(CASE WHEN star_rate = 5 THEN 1 ELSE 0 END) AS five_star
        FROM ratings
    """

    if selected_rating != 'all':
        rating_query += " WHERE star_rate = %s"
        cursor.execute(rating_query + " LIMIT 8", (selected_rating,))
    else:
        rating_query += " GROUP BY place LIMIT 8"

    cursor.execute(rating_query)
    ratings_per_place = cursor.fetchall()
    cursor.close()

    place_names = [place[0] for place in ratings_per_place]  
    visit_counts = [place[1] for place in ratings_per_place]  

    conn.close() 

    return render_template(
        'dashboard.html', 
        title='Dashboard', 
        user_profiles=user_profiles,
        total_recommendations=total_recommendations,
        total_comments=total_comments,
        total_logins=total_logins,
        star_counts=star_counts,
        place_names=place_names,
        visit_counts=visit_counts,
        gender_data=gender_data,
        address_data=address_data,
        monthly_visitors=monthly_visitors,
        ratings_per_place=ratings_per_place
    )
    
@adm.route('/feedback', methods=['GET'])
def feedback():
    conn = create_connection()  
    cursor = conn.cursor()
    
    selected_month = request.args.get('month', None)
    place = request.args.get('place', '').strip()

    if selected_month:
        if place:
            query = """
                SELECT id, name, created_at, place, comment, recommendation 
                FROM ratings 
                WHERE MONTH(created_at) = %s AND place LIKE %s
            """
            cursor.execute(query, (selected_month, f"%{place}%"))
        else:
            query = """
                SELECT id, name, created_at, place, comment, recommendation 
                FROM ratings 
                WHERE MONTH(created_at) = %s
            """
            cursor.execute(query, (selected_month,))
    else:
        if place:
            query = """
                SELECT id, name, created_at, place, comment, recommendation 
                FROM ratings 
                WHERE place LIKE %s
            """
            cursor.execute(query, (f"%{place}%",))
        else:
            query = "SELECT id, name, created_at, place, comment, recommendation FROM ratings"
            cursor.execute(query)

    feedbacks = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template('feedback.html', title='Feedback', feedbacks=feedbacks, selected_month=selected_month)

@adm.route('/review', methods=['GET'])
def review():
    conn = create_connection()
    cursor = conn.cursor()

    star_filter = request.args.get('star_filter', type=int)
    place_filter = request.args.get('place_filter', type=str)

    query = "SELECT id, name, created_at, place, star_rate FROM ratings WHERE 1=1"
    params = []

    if star_filter:
        query += " AND star_rate = %s"
        params.append(star_filter)

    if place_filter:
        query += " AND place LIKE %s"
        params.append(f"%{place_filter}%")

    cursor.execute(query, tuple(params))
    reviews = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('review.html', title='Review', reviews=reviews, star_filter=star_filter, place_filter=place_filter)

@adm.route('/reports')
def reports():
    conn = create_connection()
    cursor = conn.cursor()

    rating_query = """
    SELECT place, 
           SUM(CASE WHEN star_rate = 1 THEN 1 ELSE 0 END) AS one_star,
           SUM(CASE WHEN star_rate = 2 THEN 1 ELSE 0 END) AS two_star,
           SUM(CASE WHEN star_rate = 3 THEN 1 ELSE 0 END) AS three_star,
           SUM(CASE WHEN star_rate = 4 THEN 1 ELSE 0 END) AS four_star,
           SUM(CASE WHEN star_rate = 5 THEN 1 ELSE 0 END) AS five_star
    FROM ratings
    GROUP BY place
    """
    
    cursor.execute(rating_query)
    ratings_per_place = cursor.fetchall()

    user_profile_query = "SELECT userID, adventurerID, gender, contact_number, address, age FROM userprofile"
    cursor.execute(user_profile_query)
    user_profiles = cursor.fetchall()

    address_data = {'residents': 0, 'visitors': 0}
    for _, _, _, _, address, _ in user_profiles:
        if 'lipa' in address.lower():  
            address_data['residents'] += 1
        else:
            address_data['visitors'] += 1

    gender_query = """
    SELECT LOWER(gender) as gender, COUNT(*) 
    FROM userprofile 
    GROUP BY gender
    """
    cursor.execute(gender_query)
    gender_counts = cursor.fetchall()

    gender_data = {'male': 0, 'female': 0, 'others': 0, 'prefer not': 0}
    for gender, count in gender_counts:
        if gender in gender_data:
            gender_data[gender] = count
        else:
            gender_data['others'] += count

    feedback_query = """
        SELECT MONTH(created_at) AS month, COUNT(DISTINCT name) AS visitor_count
        FROM ratings
        GROUP BY month
        ORDER BY month;
    """
    cursor.execute(feedback_query)
    feedbacks = cursor.fetchall()

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_visitors = [0] * 12  

    for feedback in feedbacks:
        month_index = feedback[0] - 1
        visitor_count = feedback[1]
        monthly_visitors[month_index] = visitor_count
    
    star_counts = {}
    for i in range(1, 6):
        cursor.execute(f"SELECT COUNT(*) FROM ratings WHERE star_rate = {i}")
        star_counts[f"{i}_star"] = cursor.fetchone()[0]

    place_query = """
    SELECT place, COUNT(*) as visit_count
    FROM ratings
    GROUP BY place
    ORDER BY visit_count DESC
    LIMIT 10;
    """
    cursor.execute(place_query)
    places = cursor.fetchall()

    place_names = [place[0] for place in places]
    visit_counts = [place[1] for place in places]

    cursor.close()  
    conn.close()

    return render_template('reports.html', 
                           title='Reports', 
                           ratings_per_place=ratings_per_place,
                           user_profiles=user_profiles,
                           gender_data=gender_data,
                           monthly_visitors=monthly_visitors,
                           address_data=address_data,
                           visit_counts=visit_counts,
                           place_names=place_names,
                           star_counts=star_counts   
    )

@adm.route('/attractions')
def attractions():
    connection = create_connection()

    if connection is None or not connection.is_connected():
        return "Failed to connect to the database", 500

    sort_order = request.args.get('sort', 'desc')  
    
    print(f"Sort order: {sort_order}")

    order_by = 'ASC' if sort_order == 'asc' else 'DESC'
    
    query = f"""
    SELECT MIN(id) AS id, place, AVG(star_rate) AS average_rating
    FROM ratings
    GROUP BY place
    ORDER BY AVG(star_rate) {order_by};
    """
    
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query)
    attractions_data = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return render_template('attractions.html', title='Attractions', attractions=attractions_data)
