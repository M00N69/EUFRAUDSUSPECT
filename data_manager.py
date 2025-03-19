import os
import sqlite3
import pandas as pd
from datetime import datetime
import json
import streamlit as st

class DataManager:
    def __init__(self, db_path=None):
        # Utiliser un chemin dans /tmp pour Streamlit Cloud
        if db_path is None:
            # Vérifier si on peut écrire dans ./data
            try:
                os.makedirs("./data", exist_ok=True)
                with open("./data/test_write.txt", "w") as f:
                    f.write("test")
                os.remove("./data/test_write.txt")
                self.db_path = "./data/database.sqlite"
            except:
                # Si non, utiliser /tmp
                self.db_path = "/tmp/eufraud_database.sqlite"
                st.info(f"Utilisation d'une base de données temporaire: {self.db_path}")
        else:
            self.db_path = db_path
        
        self.ensure_db_exists()
        self.data = None
        self.load_data()
    
    def ensure_db_exists(self):
        """Vérifie si la base de données existe, la crée si nécessaire"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Vérifier si la base de données existe et est valide
            need_init = False
            if not os.path.exists(self.db_path):
                need_init = True
            else:
                # Vérifier si la structure est valide
                try:
                    conn = sqlite3.connect(self.db_path)
                    c = conn.cursor()
                    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reports'")
                    if not c.fetchone():
                        need_init = True
                    conn.close()
                except Exception as e:
                    st.warning(f"Base de données existante invalide: {str(e)}")
                    # Renommer l'ancienne base de données
                    backup_path = self.db_path + ".backup"
                    try:
                        os.rename(self.db_path, backup_path)
                        st.info(f"Base de données sauvegardée dans {backup_path}")
                    except:
                        pass
                    need_init = True
            
            if need_init:
                st.info("Initialisation de la base de données...")
                self.init_database()
        except Exception as e:
            st.error(f"Erreur lors de la vérification de la base de données: {str(e)}")
            # Utiliser une base de données en mémoire comme solution de secours
            self.db_path = ":memory:"
            self.init_database()
    
    def init_database(self):
        """Initialise la structure de la base de données"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Table pour les rapports
        c.execute('''
        CREATE TABLE reports (
            id INTEGER PRIMARY KEY,
            report_date TEXT,
            report_year INTEGER,
            report_month INTEGER,
            file_path TEXT,
            total_suspicions INTEGER,
            date_added TEXT
        )
        ''')
        
        # Table pour les suspicions
        c.execute('''
        CREATE TABLE suspicions (
            id INTEGER PRIMARY KEY,
            report_id INTEGER,
            classification TEXT,
            product_category TEXT,
            commodity TEXT,
            issue TEXT,
            origin TEXT,
            notified_by TEXT,
            fraud_type TEXT,
            FOREIGN KEY (report_id) REFERENCES reports (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        st.success("Base de données initialisée avec succès!")
    
    def load_data(self):
        """Charge toutes les données des suspicions de la base de données"""
        conn = sqlite3.connect(self.db_path)
        
        # Vérifier si les tables existent et contiennent des données
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='suspicions'")
        table_exists = c.fetchone()
        
        if not table_exists:
            # Si la table n'existe pas encore, renvoyer un dataframe vide avec les colonnes attendues
            self.data = pd.DataFrame(columns=[
                'id', 'report_id', 'classification', 'product_category', 
                'commodity', 'issue', 'origin', 'notified_by', 'fraud_type',
                'date', 'year', 'month', 'total_suspicions'
            ])
            conn.close()
            return
        
        # Vérifier si la table contient des données
        c.execute("SELECT COUNT(*) FROM suspicions")
        count = c.fetchone()[0]
        
        if count == 0:
            # Si la table est vide, renvoyer un dataframe vide
            self.data = pd.DataFrame(columns=[
                'id', 'report_id', 'classification', 'product_category', 
                'commodity', 'issue', 'origin', 'notified_by', 'fraud_type',
                'date', 'year', 'month', 'total_suspicions'
            ])
            conn.close()
            return
        
        # Si on arrive ici, la table existe et contient des données
        try:
            query = '''
            SELECT 
                s.*, 
                r.report_date as date,
                r.report_year as year,
                r.report_month as month,
                r.total_suspicions
            FROM 
                suspicions s
            JOIN 
                reports r ON s.report_id = r.id
            '''
            
            self.data = pd.read_sql(query, conn)
        except Exception as e:
            # En cas d'erreur, initialiser avec un DataFrame vide
            self.data = pd.DataFrame(columns=[
                'id', 'report_id', 'classification', 'product_category', 
                'commodity', 'issue', 'origin', 'notified_by', 'fraud_type',
                'date', 'year', 'month', 'total_suspicions'
            ])
            st.error(f"Erreur lors du chargement des données: {str(e)}")
        finally:
            conn.close()
    
    def get_available_dates(self):
        """Renvoie la liste des dates disponibles, triées chronologiquement"""
        if self.data is None or self.data.empty:
            # Ne pas retourner la date actuelle, indiquer qu'il n'y a pas de données
            return []
        
        if 'date' not in self.data.columns:
            return []
        
        dates = sorted(self.data['date'].unique())
        # Vérifier que dates contient des valeurs non vides
        dates = [d for d in dates if d and not pd.isna(d)]
        
        # Si après filtrage il n'y a pas de dates valides, retourner une liste vide
        if not dates:
            return []
            
        return dates
    
    def get_product_categories(self):
        """Renvoie la liste des catégories de produits disponibles"""
        if self.data is None or self.data.empty or 'product_category' not in self.data.columns:
            return []
        
        # S'assurer de ne retourner que des valeurs non nulles
        categories = [cat for cat in self.data['product_category'].unique() if cat and not pd.isna(cat)]
        return sorted(categories)
    
    def get_fraud_types(self):
        """Renvoie la liste des types de fraude disponibles"""
        if self.data is None or self.data.empty or 'fraud_type' not in self.data.columns:
            return []
        
        # S'assurer de ne retourner que des valeurs non nulles
        fraud_types = [ft for ft in self.data['fraud_type'].unique() if ft and not pd.isna(ft)]
        return sorted(fraud_types)
    
    def filter_data(self, start_date=None, end_date=None, categories=None, fraud_types=None):
        """Filtre les données selon les critères spécifiés"""
        if self.data is None or self.data.empty:
            return pd.DataFrame(columns=[
                'id', 'report_id', 'classification', 'product_category', 
                'commodity', 'issue', 'origin', 'notified_by', 'fraud_type',
                'date', 'year', 'month', 'total_suspicions'
            ])
        
        filtered_data = self.data.copy()
        
        if start_date and end_date and 'date' in filtered_data.columns:
            filtered_data = filtered_data[(filtered_data['date'] >= start_date) & 
                                         (filtered_data['date'] <= end_date)]
            
        if categories and 'product_category' in filtered_data.columns:
            filtered_data = filtered_data[filtered_data['product_category'].isin(categories)]
            
        if fraud_types and 'fraud_type' in filtered_data.columns:
            filtered_data = filtered_data[filtered_data['fraud_type'].isin(fraud_types)]
            
        return filtered_data
    
    def add_report_data(self, report_date, file_path, extracted_data):
        """Ajoute les données d'un nouveau rapport à la base de données"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Extraire l'année et le mois de la date du rapport
        date_obj = datetime.strptime(report_date, "%Y-%m")
        year = date_obj.year
        month = date_obj.month
        
        # Vérifier si ce rapport existe déjà
        c.execute("SELECT id FROM reports WHERE report_year = ? AND report_month = ?", 
                  (year, month))
        existing = c.fetchone()
        
        # Validation supplémentaire des données avant insertion
        suspicions = extracted_data.get('suspicions', [])
        valid_suspicions = []
        
        for susp in suspicions:
            # Vérifier que les champs essentiels sont présents
            has_product = bool(susp.get('product_category', '').strip())
            has_issue = bool(susp.get('issue', '').strip())
            
            if has_product and has_issue:
                valid_suspicions.append(susp)
        
        # Mettre à jour avec les suspicions validées
        extracted_data['suspicions'] = valid_suspicions
        
        if existing:
            # Mise à jour plutôt qu'ajout
            report_id = existing[0]
            c.execute("""
                UPDATE reports 
                SET file_path = ?, total_suspicions = ?, date_added = ? 
                WHERE id = ?
                """, 
                (file_path, extracted_data.get('total_suspicions', 0), 
                 datetime.now().isoformat(), report_id))
            
            # Supprimer les anciennes suspicions pour ce rapport
            c.execute("DELETE FROM suspicions WHERE report_id = ?", (report_id,))
        else:
            # Insertion d'un nouveau rapport
            c.execute("""
                INSERT INTO reports (report_date, report_year, report_month, file_path, 
                                    total_suspicions, date_added)
                VALUES (?, ?, ?, ?, ?, ?)
                """, 
                (report_date, year, month, file_path, 
                 extracted_data.get('total_suspicions', 0), datetime.now().isoformat()))
            
            report_id = c.lastrowid
        
        # Insertion des suspicions
        suspicions = extracted_data.get('suspicions', [])
        for susp in suspicions:
            c.execute("""
                INSERT INTO suspicions (report_id, classification, product_category, 
                                       commodity, issue, origin, notified_by, fraud_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, 
                (report_id, susp.get('classification', ''), 
                 susp.get('product_category', ''), susp.get('commodity', ''),
                 susp.get('issue', ''), susp.get('origin', ''), 
                 susp.get('notified_by', ''), susp.get('fraud_type', '')))
        
        conn.commit()
        conn.close()
        
        # Recharger les données
        self.load_data()
        
        return True
    
    def check_report_exists(self, year, month):
        """Vérifie si un rapport pour une année et un mois spécifiques existe déjà"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT COUNT(*) FROM reports 
            WHERE report_year = ? AND report_month = ?
            """, (year, month))
        
        count = c.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def get_latest_report_date(self):
        """Obtient la date du rapport le plus récent dans la base de données"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT name FROM sqlite_master WHERE type='table' AND name='reports'
        """)
        table_exists = c.fetchone()
        
        if not table_exists:
            conn.close()
            return None, None
        
        c.execute("""
            SELECT COUNT(*) FROM reports
        """)
        count = c.fetchone()[0]
        
        if count == 0:
            conn.close()
            return None, None
        
        c.execute("""
            SELECT report_year, report_month FROM reports 
            ORDER BY report_year DESC, report_month DESC 
            LIMIT 1
            """)
        
        result = c.fetchone()
        conn.close()
        
        if result:
            return result[0], result[1]
        else:
            return None, None
            
    def reset_database(self):
        """Réinitialise complètement la base de données"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Supprimer les tables existantes
        c.execute("DROP TABLE IF EXISTS suspicions")
        c.execute("DROP TABLE IF EXISTS reports")
        
        conn.commit()
        conn.close()
        
        # Recréer la structure
        self.init_database()
        
        # Réinitialiser les données
        self.data = pd.DataFrame(columns=[
            'id', 'report_id', 'classification', 'product_category', 
            'commodity', 'issue', 'origin', 'notified_by', 'fraud_type',
            'date', 'year', 'month', 'total_suspicions'
        ])
        
        return True
