from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua-chave-secreta-super-segura-marido-aluguel-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marido_aluguel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

CORS(app, origins=['*'])
db = SQLAlchemy(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Modelos do banco de dados
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    nome_completo = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    whatsapp = db.Column(db.String(20))
    endereco = db.Column(db.Text)
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(50))
    cep = db.Column(db.String(10))
    descricao = db.Column(db.Text)
    foto_perfil = db.Column(db.String(200))
    is_prestador = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Servico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    categoria = db.Column(db.String(100))
    preco = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class MediaFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(200))
    file_type = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    servico_id = db.Column(db.Integer, db.ForeignKey('servico.id'))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Solicitacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prestador_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    servico_id = db.Column(db.Integer, db.ForeignKey('servico.id'), nullable=False)
    descricao_problema = db.Column(db.Text)
    endereco_servico = db.Column(db.Text)
    data_solicitada = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='pendente')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Decorator para verificar token JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token é necessário!'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
        except:
            return jsonify({'message': 'Token inválido!'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

# Rotas da API
@app.route('/')
def home():
    return jsonify({
        'message': 'API do Marido de Aluguel funcionando!',
        'version': '1.0.0'
    })

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Username, email e password são obrigatórios!'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Usuário já existe!'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email já cadastrado!'}), 400
    
    hashed_password = generate_password_hash(data['password'])
    
    new_user = User(
        username=data['username'],
        email=data['email'],
        password_hash=hashed_password,
        nome_completo=data.get('nome_completo', ''),
        telefone=data.get('telefone', ''),
        whatsapp=data.get('whatsapp', ''),
        is_prestador=data.get('is_prestador', False)
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'Usuário criado com sucesso!'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    
    user = User.query.filter_by(username=data['username']).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'nome_completo': user.nome_completo,
                'is_prestador': user.is_prestador
            }
        })
    
    return jsonify({'message': 'Credenciais inválidas!'}), 401

@app.route('/api/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'nome_completo': current_user.nome_completo,
        'telefone': current_user.telefone,
        'whatsapp': current_user.whatsapp,
        'endereco': current_user.endereco,
        'cidade': current_user.cidade,
        'estado': current_user.estado,
        'cep': current_user.cep,
        'descricao': current_user.descricao,
        'foto_perfil': current_user.foto_perfil,
        'is_prestador': current_user.is_prestador
    })

@app.route('/api/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    data = request.get_json()
    
    current_user.nome_completo = data.get('nome_completo', current_user.nome_completo)
    current_user.telefone = data.get('telefone', current_user.telefone)
    current_user.whatsapp = data.get('whatsapp', current_user.whatsapp)
    current_user.endereco = data.get('endereco', current_user.endereco)
    current_user.cidade = data.get('cidade', current_user.cidade)
    current_user.estado = data.get('estado', current_user.estado)
    current_user.cep = data.get('cep', current_user.cep)
    current_user.descricao = data.get('descricao', current_user.descricao)
    
    db.session.commit()
    
    return jsonify({'message': 'Perfil atualizado com sucesso!'})

@app.route('/api/servicos', methods=['GET'])
def get_servicos():
    servicos = Servico.query.all()
    result = []
    
    for servico in servicos:
        user = User.query.get(servico.user_id)
        medias = MediaFile.query.filter_by(servico_id=servico.id).all()
        
        result.append({
            'id': servico.id,
            'titulo': servico.titulo,
            'descricao': servico.descricao,
            'categoria': servico.categoria,
            'preco': servico.preco,
            'prestador': {
                'id': user.id,
                'nome': user.nome_completo,
                'telefone': user.telefone,
                'whatsapp': user.whatsapp,
                'cidade': user.cidade
            },
            'medias': [{'filename': m.filename, 'type': m.file_type} for m in medias],
            'created_at': servico.created_at.isoformat()
        })
    
    return jsonify(result)

@app.route('/api/servicos', methods=['POST'])
@token_required
def create_servico(current_user):
    data = request.get_json()
    
    new_servico = Servico(
        titulo=data['titulo'],
        descricao=data.get('descricao', ''),
        categoria=data.get('categoria', ''),
        preco=data.get('preco', 0),
        user_id=current_user.id
    )
    
    db.session.add(new_servico)
    db.session.commit()
    
    return jsonify({'message': 'Serviço criado com sucesso!', 'id': new_servico.id}), 201

@app.route('/api/upload', methods=['POST'])
@token_required
def upload_file(current_user):
    if 'file' not in request.files:
        return jsonify({'message': 'Nenhum arquivo enviado!'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'Nenhum arquivo selecionado!'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        file_type = 'image' if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')) else 'video'
        
        media_file = MediaFile(
            filename=filename,
            original_filename=file.filename,
            file_type=file_type,
            user_id=current_user.id,
            servico_id=request.form.get('servico_id')
        )
        
        db.session.add(media_file)
        db.session.commit()
        
        return jsonify({
            'message': 'Arquivo enviado com sucesso!',
            'filename': filename,
            'url': f'/uploads/{filename}'
        }), 201

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
