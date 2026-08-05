DEMO_COLLECTIONS = [
    {"month": "Jan", "amount_lakhs": 32},
    {"month": "Feb", "amount_lakhs": 38},
    {"month": "Mar", "amount_lakhs": 41},
    {"month": "Apr", "amount_lakhs": 45},
    {"month": "May", "amount_lakhs": 44},
    {"month": "Jun", "amount_lakhs": 48},
    {"month": "Jul", "amount_lakhs": 48.2},
]

# Outstanding totals per class (₹): 10=3.2L, 12=2.8L, 9=1.9L, 11=1.5L, 8=1.1L, Other=1.9L
# 41 families total, 18 predicted defaulters, 8 scholarships.
DEMO_ACCOUNTS = [
    # Class 10 — 3.2L across 8 families, 5 predicted defaulters, 2 scholarships
    {"student_name": "Aarav Sharma", "class_name": "10", "family_email": "sharma.fam@example.com", "outstanding": 52000, "overdue_days": 95, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Ananya Iyer", "class_name": "10", "family_email": "iyer.fam@example.com", "outstanding": 41000, "overdue_days": 70, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Vihaan Patel", "class_name": "10", "family_email": "patel.fam@example.com", "outstanding": 38000, "overdue_days": 55, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Ishaan Rao", "class_name": "10", "family_email": "rao.fam@example.com", "outstanding": 35000, "overdue_days": 40, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Diya Mehta", "class_name": "10", "family_email": "mehta.fam@example.com", "outstanding": 33000, "overdue_days": 30, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Kabir Gupta", "class_name": "10", "family_email": "gupta.fam@example.com", "outstanding": 45000, "overdue_days": 12, "predicted_default": 0, "scholarship": 1},
    {"student_name": "Myra Reddy", "class_name": "10", "family_email": "reddy.fam@example.com", "outstanding": 41000, "overdue_days": 8, "predicted_default": 0, "scholarship": 0},
    {"student_name": "Arjun Nair", "class_name": "10", "family_email": "nair.fam@example.com", "outstanding": 35000, "overdue_days": 5, "predicted_default": 0, "scholarship": 1},
    # Class 12 — 2.8L across 7 families, 5 predicted defaulters, 1 scholarship
    {"student_name": "Sneha Kulkarni", "class_name": "12", "family_email": "kulkarni.fam@example.com", "outstanding": 48000, "overdue_days": 110, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Rohan Das", "class_name": "12", "family_email": "das.fam@example.com", "outstanding": 42000, "overdue_days": 88, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Priya Singh", "class_name": "12", "family_email": "singh.fam@example.com", "outstanding": 39000, "overdue_days": 65, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Aditya Kumar", "class_name": "12", "family_email": "kumar.fam@example.com", "outstanding": 37000, "overdue_days": 50, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Riya Malhotra", "class_name": "12", "family_email": "malhotra.fam@example.com", "outstanding": 34000, "overdue_days": 35, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Karan Shah", "class_name": "12", "family_email": "shah.fam@example.com", "outstanding": 45000, "overdue_days": 15, "predicted_default": 0, "scholarship": 1},
    {"student_name": "Pooja Joshi", "class_name": "12", "family_email": "joshi.fam@example.com", "outstanding": 35000, "overdue_days": 6, "predicted_default": 0, "scholarship": 0},
    # Class 9 — 1.9L across 6 families, 3 predicted defaulters, 1 scholarship
    {"student_name": "Dev Bansal", "class_name": "9", "family_email": "bansal.fam@example.com", "outstanding": 38000, "overdue_days": 75, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Aisha Verma", "class_name": "9", "family_email": "verma.fam@example.com", "outstanding": 34000, "overdue_days": 60, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Rahul Tiwari", "class_name": "9", "family_email": "tiwari.fam@example.com", "outstanding": 31000, "overdue_days": 45, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Anushka Sen", "class_name": "9", "family_email": "sen.fam@example.com", "outstanding": 32000, "overdue_days": 20, "predicted_default": 0, "scholarship": 1},
    {"student_name": "Ishita Ghosh", "class_name": "9", "family_email": "ghosh.fam@example.com", "outstanding": 30000, "overdue_days": 10, "predicted_default": 0, "scholarship": 0},
    {"student_name": "Ved Mishra", "class_name": "9", "family_email": "mishra.fam@example.com", "outstanding": 25000, "overdue_days": 4, "predicted_default": 0, "scholarship": 0},
    # Class 11 — 1.5L across 5 families, 2 predicted defaulters, 1 scholarship
    {"student_name": "Tanvi Desai", "class_name": "11", "family_email": "desai.fam@example.com", "outstanding": 35000, "overdue_days": 82, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Aryan Kapoor", "class_name": "11", "family_email": "kapoor.fam@example.com", "outstanding": 32000, "overdue_days": 58, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Navya Bhat", "class_name": "11", "family_email": "bhat.fam@example.com", "outstanding": 31000, "overdue_days": 22, "predicted_default": 0, "scholarship": 1},
    {"student_name": "Arnav Chawla", "class_name": "11", "family_email": "chawla.fam@example.com", "outstanding": 27000, "overdue_days": 9, "predicted_default": 0, "scholarship": 0},
    {"student_name": "Sia Saxena", "class_name": "11", "family_email": "saxena.fam@example.com", "outstanding": 25000, "overdue_days": 3, "predicted_default": 0, "scholarship": 0},
    # Class 8 — 1.1L across 5 families, 2 predicted defaulters, 1 scholarship
    {"student_name": "Advik Jain", "class_name": "8", "family_email": "jain.fam@example.com", "outstanding": 28000, "overdue_days": 68, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Ira Hegde", "class_name": "8", "family_email": "hegde.fam@example.com", "outstanding": 26000, "overdue_days": 52, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Reyansh Pillai", "class_name": "8", "family_email": "pillai.fam@example.com", "outstanding": 22000, "overdue_days": 18, "predicted_default": 0, "scholarship": 1},
    {"student_name": "Kiara Bose", "class_name": "8", "family_email": "bose.fam@example.com", "outstanding": 19000, "overdue_days": 7, "predicted_default": 0, "scholarship": 0},
    {"student_name": "Kabir Dutta", "class_name": "8", "family_email": "dutta.fam@example.com", "outstanding": 15000, "overdue_days": 2, "predicted_default": 0, "scholarship": 0},
    # Other — 1.9L across 10 families, 1 predicted defaulter, 1 scholarship
    {"student_name": "Nisha Kadam", "class_name": "7", "family_email": "kadam.fam@example.com", "outstanding": 24000, "overdue_days": 62, "predicted_default": 1, "scholarship": 0},
    {"student_name": "Yash Thakur", "class_name": "7", "family_email": "thakur.fam@example.com", "outstanding": 23000, "overdue_days": 28, "predicted_default": 0, "scholarship": 1},
    {"student_name": "Mira Kaur", "class_name": "6", "family_email": "kaur.fam@example.com", "outstanding": 22000, "overdue_days": 14, "predicted_default": 0, "scholarship": 0},
    {"student_name": "Ayaan Sheikh", "class_name": "6", "family_email": "sheikh.fam@example.com", "outstanding": 20000, "overdue_days": 6, "predicted_default": 0, "scholarship": 0},
    {"student_name": "Sara Fernandes", "class_name": "5", "family_email": "fernandes.fam@example.com", "outstanding": 21000, "overdue_days": 11, "predicted_default": 0, "scholarship": 1},
    {"student_name": "Ivan D'Souza", "class_name": "5", "family_email": "dsouza.fam@example.com", "outstanding": 19000, "overdue_days": 5, "predicted_default": 0, "scholarship": 0},
    {"student_name": "Ritika Paul", "class_name": "4", "family_email": "paul.fam@example.com", "outstanding": 18000, "overdue_days": 9, "predicted_default": 0, "scholarship": 0},
    {"student_name": "Harsh Anand", "class_name": "4", "family_email": "anand.fam@example.com", "outstanding": 17000, "overdue_days": 3, "predicted_default": 0, "scholarship": 0},
    {"student_name": "Tara Menon", "class_name": "3", "family_email": "menon.fam@example.com", "outstanding": 16000, "overdue_days": 2, "predicted_default": 0, "scholarship": 0},
    {"student_name": "Vivaan Lobo", "class_name": "2", "family_email": "lobo.fam@example.com", "outstanding": 10000, "overdue_days": 1, "predicted_default": 0, "scholarship": 0},
]
