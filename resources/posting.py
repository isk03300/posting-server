from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from config import Config
from mysql_connection import get_connection
from mysql.connector import Error


from datetime import datetime
import boto3


class PostingResource(Resource) :

    @jwt_required()
    def post(self) :

        file = request.files.get('photo')
        content = request.form.get('content')
        user_id = get_jwt_identity()

        if file is None :
            return {'error' : '파일을 찾을 수 없습니다.'}, 400
        
        current_tiem = datetime.now()
        new_file_name = current_tiem.isoformat().replace(':','-') + 'id:' + str(user_id) + '.jpg'
        file.filename = new_file_name

        s3 = boto3.client( 's3', 
                     aws_access_key_id = Config.AWS_ACCESS_KEY_ID,
                     aws_secret_access_key = Config.AWS_SECRET_ACCESS_KEY)

        try :
            s3.upload_fileobj(file, Config.S3_BUCKET, 
                              file.filename, 
                              ExtraArgs = {'ACL' : 'public-read', 'ContentType' : 'image/jpeg'} )

        except Exception as e :
            print(e)
            return {'error' : str(e)}, 500
        
        
        # rekognition 서비스를 이용해서
        # object detection 하여. 태그 이름을 가져온다.

        tag_list = self.detect_labels(file.filename,Config.S3_BUCKET)
        print()
        print(tag_list)
        print()
        print(len(tag_list))

        # DB의 posting 테이블에 데이터를 넣어야 하고,
        # tag_name 테이블과 tag 테이블에도 데이터를 넣어줘야 한다.
        try :
            connection = get_connection()

            # 1.posting 테이블에 데이터를 넣어준다.

            query = '''insert into posting
                        (userId,imgUrl,content)
                        values
                        (%s,%s,%s);'''
            
            imgUrl = Config.S3_LOCATION + file.filename
            
            record = (user_id, imgUrl , content)

            cursor = connection.cursor()
            cursor.execute(query,record)

            posting_id = cursor.lastrowid
            print()
            print(posting_id)




           

            # 2. tag_name 테이블 처리를 해준다.
            #    리코그니션을 이용해서 받아온 label이,
            #    tag_name에 이미 존재하면, 그 아이디만 가져오고
            #    그렇지 않으면, 테이블에 인서트 한 후에
            #    그 아이디를 가져온다.


            for tag in tag_list :
                tag = tag.lower()
                query = '''select *
                            from tag_name
                            where name = %s;'''
                
                record = (tag,)
                cursor = connection.cursor(dictionary=True)
                cursor.execute(query,record)
                result_list = cursor.fetchall()
                print()
                print(result_list)
                print('---------------')
                print(result_list[0])
                print('-------------')
                print(result_list[0]['id'])
                print('------------------------')
                print(len(result_list))

                # 태그가 이미 테이블에 있으면, id만 가져오고
                if len(result_list) !=0 :
                    tag_name_id = result_list[0]['id']
                else :
                    # 태그가 없으면, 인서트 한다.
                    query = '''insert into tag_name
                                            (name)
                                            values
                                            (%s);'''
                    record = (tag, )
                    cursor = connection.cursor()
                    cursor.execute(query,record)

                    tag_name_id = cursor.lastrowid


            # 3. 위의 태그네임 아이디와, 포스팅 아이디를 이용해서,
            # #    tag 테이블에 데이터를 넣어준다.
                    

                query = '''insert into tag
                            (postingId,tagNameId)
                            values
                            (%s,%s);'''
                
                record = (posting_id,tag_name_id)
                cursor = connection.cursor()
                cursor.execute(query,record)
            

                    
            # 트랜잭션 처리를 위해서 
            # commit 는 테이블 처리를 다 하고나서
            # 마지막에 해준다.
            # 이렇게 해주면, 중간에 다른 테이블에서 문제 발생 시,
            # 모든 테이블이 원상복구 된다.(롤백)
            # 이 기능을 **트랜잭션** 이라고 한다.
            connection.commit()

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 400   
        
        return {'result' : 'success'},200
        
    def detect_labels(self, photo, bucket):

        client = boto3.client('rekognition',
                     'ap-northeast-2',
                     aws_access_key_id = Config.AWS_ACCESS_KEY_ID,
                     aws_secret_access_key = Config.AWS_SECRET_ACCESS_KEY)

        response = client.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':photo}},
        MaxLabels=5,
        # Uncomment to use image properties and filtration settings
        #Features=["GENERAL_LABELS", "IMAGE_PROPERTIES"],
        #Settings={"GeneralLabels": {"LabelInclusionFilters":["Cat"]},
        # "ImageProperties": {"MaxDominantColors":10}}
        )

        print('Detected labels for ' + photo)
        print()

        label_list = []
        for label in response['Labels']:
            print("Label: " + label['Name'])
            print("Confidence: " + str(label['Confidence']))

            if label['Confidence'] >= 90 :
                label_list.append(label['Name'])
            

        return label_list

       
    @jwt_required()
    def get(self) :

        user_id = get_jwt_identity()

        offset = request.args.get('offset')
        limit = request.args.get('limit')

        try :
            connection = get_connection()
            query = '''select p.id as postId, p.imgUrl,
                        p.content, u.id as userid, u.email ,
                        p.createdAt, count(l.id) as likeCnt,
                        if(l2.id is null,0,1) as isLike
                        from follow f
                        join posting p
                        on f.followeeId = p.userId
                        join user u
                        on u.id = p.userId
                        left join `like` l
                        on p.id = l.postingId
                        left join `like` l2
                        on p.id = l.postingId and l2.userId = %s
                        where f.followerId = %s
                        group by p.id
                        order by p.createdAt desc
                        limit '''+str(offset)+''','''+str(limit)+''';'''
                                    
            record = (user_id, user_id)

            cursor = connection.cursor(dictionary=True)

            cursor.execute(query,record)

            result_list = cursor.fetchall()

            print(result_list)

            i = 0
            for row in result_list :
                result_list[i]['createdAt']=row['createdAt'].isoformat()
                i = i + 1

            print(result_list)

            cursor.close()
            connection.close()

        except Error as e :
            print(e) 
            cursor.close()
            connection.close()
            return {'error' : str(e)},400
        
        return {'result' : 'success',
                'items' : result_list,
                'count' : len(result_list)}, 200
        
class PostingMainResource(Resource) :
    @jwt_required()
    def get(self,posting_id):

        user_id = get_jwt_identity()


        try :
            connection = get_connection()
            query = '''select p.id as postId, p.imgUrl, p.content,
                        u.id,u.email,p.createdAt,
                        count(l.id) as likeCnt,
                        if(l2.id is null,0,1) as isLike
                        from posting p
                        join user u
                        on p.userId = u.id
                        left join `like` l
                        on p.id = l.postingId
                        left join `like` l2
                        on p.id = l2.postingId and l2.userId = %s
                        where p.id = %s;'''
                        
                                    
            record = (user_id, posting_id)

            cursor = connection.cursor(dictionary=True)

            cursor.execute(query,record)

            result_list = cursor.fetchall()

            if len(result_list) == 0 :
                return {'error' : '데이터 없음'},400


            # todo : 데이터 변수 작업.
            post = result_list[0]

            query = '''select concat('#', tg.name) as tag 
                                from tag t
                                join tag_name tg
                                on t.tagNameId = tg.id
                                where t.postingId = %s;'''
            
            record = (posting_id, )

            cursor = connection.cursor(dictionary=True)
            cursor.execute(query,record)
            tag_list = cursor.fetchall()
            print()
           

            tag =[]
            for tag_dict in tag_list :
                tag.append( tag_dict['tag'] )
            
            print()
            print(result_list)
            print()
            print(result_list[0])
            print(post)
            print()
            print(tag_list)
            print()
            print(tag)

            post['createdAt'] = post['createdAt'].isoformat()


            cursor.close()
            connection.close()

        except Error as e :
            print(e) 
            cursor.close()
            connection.close()
            return {'error' : str(e)},400
        
        
        return {'result' : 'success',
                    'post' : post,
                    'tag' : tag}, 200
       


    