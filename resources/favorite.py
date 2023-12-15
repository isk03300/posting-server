from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from config import Config
from mysql_connection import get_connection
from mysql.connector import Error



from datetime import datetime
import boto3

class FavoriteResource(Resource) :
    
    @jwt_required()
    def post(self) :
        
        postingId = request.args.get('postingId')
        user_id = get_jwt_identity()

        try :
            connection = get_connection()

            query = '''insert into favorite
                                (userId, postingId)
                                values
                                (%s,%s);'''
            
            record = (user_id, postingId)

            cursor = connection.cursor()
            cursor.execute(query,record)

            connection.commit()

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {'error' : (e)} , 400

        return {'result' : 'success'},200
    
    @jwt_required()
    def delete(self) :

        postingId = request.args.get('postingId')
        user_id = get_jwt_identity()

        try :
            connection = get_connection()

            query = '''delete 
                        from favorite
                        where userId = %s and postingId = %s;'''
            
            record = (user_id,postingId)

            cursor = connection.cursor()
            cursor.execute(query,record)

            connection.commit()

            cursor.close()
            connection.close()


        except Error as e:

            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 400

        return {'result' : 'success'}, 200