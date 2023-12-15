from flask import Flask
from flask_jwt_extended import JWTManager
from flask_restful import Api
from config import Config
from resources.favorite import FavoriteResource
from resources.follow import FollowResoucre
from resources.posting import PostingResource
from resources.user import UserLoginResource, UserRegisterResource, userLogoutResource


# 로그아웃 관련된 import문
from resources.user import jwt_blocklist

app = Flask(__name__)

app.config.from_object(Config)
jwt = JWTManager(app)

# 로그아웃된 토큰으로 요청하는 경우,
# 실행되지 않도록 처리하는 코드
@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header,jwt_payload) :
    jti = jwt_payload['jti']
    return jti in jwt_blocklist



api = Api(app)
api.add_resource(  UserRegisterResource , '/user/register')
api.add_resource(UserLoginResource ,'/user/login' )
api.add_resource(userLogoutResource , '/user/logout')
api.add_resource(PostingResource , '/posting')
api.add_resource( FavoriteResource , '/favorite')
api.add_resource( FollowResoucre , '/follow')
if __name__ == '__main__' :
    app.run()
