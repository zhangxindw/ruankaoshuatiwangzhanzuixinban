import os
import uuid
import random
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from models import db, Question, Chapter, QuestionType, WrongQuestion, FavoriteQuestion, UserAnswer, UserPreference, OperationLog
from openpyxl import load_workbook, Workbook

app = Flask(__name__)
app.config['SECRET_KEY'] = 'quiz-system-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

CORS(app)
db.init_app(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def log_operation(user_id, action, target_type=None, target_id=None, details=None):
    log = OperationLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details
    )
    db.session.add(log)
    db.session.commit()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['xls', 'xlsx']

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Quiz System API is running'})

@app.route('/api/init-db', methods=['POST'])
def init_database():
    db.create_all()
    if QuestionType.query.count() == 0:
        default_types = [
            QuestionType(name='单选题', is_multiple=False),
            QuestionType(name='多选题', is_multiple=True),
            QuestionType(name='判断题', is_multiple=False)
        ]
        db.session.add_all(default_types)
    if Chapter.query.count() == 0:
        default_chapter = Chapter(name='默认章节', order=0)
        db.session.add(default_chapter)
    if UserPreference.query.count() == 0:
        default_pref = UserPreference(user_id='default_user')
        db.session.add(default_pref)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': 'Database initialized'})

@app.route('/api/chapters', methods=['GET', 'POST'])
def handle_chapters():
    if request.method == 'GET':
        chapters = Chapter.query.filter_by(parent_id=None).order_by(Chapter.order).all()
        chapters_data = []
        for c in chapters:
            chapter_dict = c.to_dict()
            # 统计该章节的题目数量
            question_count = Question.query.filter_by(chapter_id=c.id).count()
            chapter_dict['question_count'] = question_count
            chapters_data.append(chapter_dict)
        return jsonify({'status': 'ok', 'data': chapters_data})
    else:
        data = request.json
        chapter = Chapter(
            name=data.get('name'),
            parent_id=data.get('parent_id'),
            order=data.get('order', 0)
        )
        db.session.add(chapter)
        db.session.commit()
        log_operation('admin', 'create_chapter', 'chapter', chapter.id, f'Created chapter: {chapter.name}')
        return jsonify({'status': 'ok', 'data': chapter.to_dict()})

@app.route('/api/chapters/<int:chapter_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    if request.method == 'GET':
        return jsonify({'status': 'ok', 'data': chapter.to_dict()})
    elif request.method == 'PUT':
        data = request.json
        chapter.name = data.get('name', chapter.name)
        chapter.parent_id = data.get('parent_id', chapter.parent_id)
        chapter.order = data.get('order', chapter.order)
        db.session.commit()
        log_operation('admin', 'update_chapter', 'chapter', chapter.id, f'Updated chapter: {chapter.name}')
        return jsonify({'status': 'ok', 'data': chapter.to_dict()})
    else:
        log_operation('admin', 'delete_chapter', 'chapter', chapter.id, f'Deleted chapter: {chapter.name}')
        db.session.delete(chapter)
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'Chapter deleted'})

@app.route('/api/question-types', methods=['GET', 'POST'])
def handle_question_types():
    if request.method == 'GET':
        types = QuestionType.query.all()
        return jsonify({'status': 'ok', 'data': [t.to_dict() for t in types]})
    else:
        data = request.json
        qtype = QuestionType(
            name=data.get('name'),
            is_multiple=data.get('is_multiple', False)
        )
        db.session.add(qtype)
        db.session.commit()
        log_operation('admin', 'create_question_type', 'question_type', qtype.id, f'Created question type: {qtype.name}')
        return jsonify({'status': 'ok', 'data': qtype.to_dict()})

@app.route('/api/question-types/<int:type_id>', methods=['PUT', 'DELETE'])
def handle_question_type(type_id):
    qtype = QuestionType.query.get_or_404(type_id)
    if request.method == 'PUT':
        data = request.json
        qtype.name = data.get('name', qtype.name)
        qtype.is_multiple = data.get('is_multiple', qtype.is_multiple)
        db.session.commit()
        log_operation('admin', 'update_question_type', 'question_type', qtype.id, f'Updated question type: {qtype.name}')
        return jsonify({'status': 'ok', 'data': qtype.to_dict()})
    else:
        log_operation('admin', 'delete_question_type', 'question_type', qtype.id, f'Deleted question type: {qtype.name}')
        db.session.delete(qtype)
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'Question type deleted'})

@app.route('/api/questions', methods=['GET', 'POST'])
def handle_questions():
    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        stem = request.args.get('stem', '')
        chapter_id = request.args.get('chapter_id', type=int)
        question_type_id = request.args.get('question_type_id', type=int)
        status = request.args.get('status', '')

        query = Question.query
        if stem:
            query = query.filter(Question.stem.contains(stem))
        if chapter_id is not None and chapter_id > 0:
            query = query.filter_by(chapter_id=chapter_id)
        elif chapter_id == 0:
            query = query.filter_by(chapter_id=None)
        if question_type_id:
            query = query.filter_by(question_type_id=question_type_id)
        if status:
            query = query.filter_by(status=status)

        pagination = query.order_by(Question.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'status': 'ok',
            'data': [q.to_dict() for q in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    else:
        data = request.json
        question = Question(
            stem=data.get('stem'),
            option_a=data.get('option_a'),
            option_b=data.get('option_b'),
            option_c=data.get('option_c'),
            option_d=data.get('option_d'),
            option_e=data.get('option_e'),
            option_f=data.get('option_f'),
            answer=data.get('answer', '').upper(),
            explanation=data.get('explanation'),
            stem_html=data.get('stem_html'),
            option_a_html=data.get('option_a_html'),
            option_b_html=data.get('option_b_html'),
            option_c_html=data.get('option_c_html'),
            option_d_html=data.get('option_d_html'),
            option_e_html=data.get('option_e_html'),
            option_f_html=data.get('option_f_html'),
            explanation_html=data.get('explanation_html'),
            difficulty=data.get('difficulty', 1),
            status=data.get('status', 'published'),
            chapter_id=data.get('chapter_id'),
            question_type_id=data.get('question_type_id')
        )
        db.session.add(question)
        db.session.commit()
        log_operation('admin', 'create_question', 'question', question.id, f'Created question: {question.stem[:50]}')
        return jsonify({'status': 'ok', 'data': question.to_dict()})

@app.route('/api/questions/<int:question_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_question(question_id):
    question = Question.query.get_or_404(question_id)
    if request.method == 'GET':
        return jsonify({'status': 'ok', 'data': question.to_dict()})
    elif request.method == 'PUT':
        data = request.json
        question.stem = data.get('stem', question.stem)
        question.option_a = data.get('option_a', question.option_a)
        question.option_b = data.get('option_b', question.option_b)
        question.option_c = data.get('option_c', question.option_c)
        question.option_d = data.get('option_d', question.option_d)
        question.option_e = data.get('option_e', question.option_e)
        question.option_f = data.get('option_f', question.option_f)
        question.answer = data.get('answer', question.answer).upper()
        question.explanation = data.get('explanation', question.explanation)
        question.stem_html = data.get('stem_html', question.stem_html)
        question.option_a_html = data.get('option_a_html', question.option_a_html)
        question.option_b_html = data.get('option_b_html', question.option_b_html)
        question.option_c_html = data.get('option_c_html', question.option_c_html)
        question.option_d_html = data.get('option_d_html', question.option_d_html)
        question.option_e_html = data.get('option_e_html', question.option_e_html)
        question.option_f_html = data.get('option_f_html', question.option_f_html)
        question.explanation_html = data.get('explanation_html', question.explanation_html)
        question.difficulty = data.get('difficulty', question.difficulty)
        question.status = data.get('status', question.status)
        question.chapter_id = data.get('chapter_id', question.chapter_id)
        question.question_type_id = data.get('question_type_id', question.question_type_id)
        db.session.commit()
        log_operation('admin', 'update_question', 'question', question.id, f'Updated question: {question.stem[:50]}')
        return jsonify({'status': 'ok', 'data': question.to_dict()})
    else:
        # 删除关联的错题记录
        WrongQuestion.query.filter_by(question_id=question.id).delete()
        # 删除关联的收藏记录
        FavoriteQuestion.query.filter_by(question_id=question.id).delete()
        # 删除关联的答题记录
        UserAnswer.query.filter_by(question_id=question.id).delete()
        # 记录操作日志
        log_operation('admin', 'delete_question', 'question', question.id, f'Deleted question: {question.stem[:50]}')
        # 删除题目
        db.session.delete(question)
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'Question deleted'})

@app.route('/api/questions/batch', methods=['POST'])
def batch_operate_questions():
    data = request.json
    question_ids = data.get('question_ids', [])
    action = data.get('action')

    if not question_ids or not action:
        return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400

    questions = Question.query.filter(Question.id.in_(question_ids)).all()

    if action == 'delete':
        for q in questions:
            # 删除关联的错题记录
            WrongQuestion.query.filter_by(question_id=q.id).delete()
            # 删除关联的收藏记录
            FavoriteQuestion.query.filter_by(question_id=q.id).delete()
            # 删除关联的答题记录
            UserAnswer.query.filter_by(question_id=q.id).delete()
            # 记录操作日志
            log_operation('admin', 'delete_question', 'question', q.id, f'Batch deleted question: {q.stem[:50]}')
            # 删除题目
            db.session.delete(q)
        db.session.commit()
        return jsonify({'status': 'ok', 'message': f'Deleted {len(questions)} questions'})
    elif action == 'move_chapter':
        chapter_id = data.get('chapter_id')
        for q in questions:
            q.chapter_id = chapter_id
        db.session.commit()
        return jsonify({'status': 'ok', 'message': f'Moved {len(questions)} questions to chapter {chapter_id}'})
    elif action == 'change_type':
        question_type_id = data.get('question_type_id')
        for q in questions:
            q.question_type_id = question_type_id
        db.session.commit()
        return jsonify({'status': 'ok', 'message': f'Changed type for {len(questions)} questions'})
    elif action == 'change_status':
        status = data.get('status')
        for q in questions:
            q.status = status
        db.session.commit()
        return jsonify({'status': 'ok', 'message': f'Changed status for {len(questions)} questions'})

    return jsonify({'status': 'error', 'message': 'Unknown action'}), 400

@app.route('/api/import/template', methods=['GET'])
def download_template():
    wb = Workbook()
    ws = wb.active
    ws.title = "题目导入模板"

    headers = ['题干', '选项A', '选项B', '选项C', '选项D', '选项E', '选项F', '答案', '解析', '题型']
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)

    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 20
    ws.column_dimensions['G'].width = 15
    ws.column_dimensions['H'].width = 15
    ws.column_dimensions['I'].width = 30
    ws.column_dimensions['J'].width = 15

    template_path = os.path.join(app.config['UPLOAD_FOLDER'], 'question_template.xlsx')
    wb.save(template_path)
    return send_file(template_path, as_attachment=True, download_name='question_template.xlsx')

@app.route('/api/import/upload', methods=['POST'])
def upload_questions():
    try:
        print(f"收到上传请求")
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400

        file = request.files['file']
        print(f"文件名: {file.filename}")
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'status': 'error', 'message': 'Invalid file type'}), 400

        duplicate_handling = request.form.get('duplicate_handling', 'skip')
        print(f"重复处理方式: {duplicate_handling}")

        # 为上传的文件生成唯一的临时文件名，避免文件名冲突
        import uuid
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        print(f"文件保存成功: {filepath}")

        wb = None
        try:
            # 确保数据库已初始化
            if QuestionType.query.count() == 0:
                default_types = [
                    QuestionType(name='单选题', is_multiple=False),
                    QuestionType(name='多选题', is_multiple=True),
                    QuestionType(name='判断题', is_multiple=False)
                ]
                db.session.add_all(default_types)
                db.session.commit()

            print("正在加载Excel文件...")
            wb = load_workbook(filepath, data_only=True)
            ws = wb.active

            headers = [cell.value for cell in ws[1]]
            print(f"表头: {headers}")
            header_map = {}
            for idx, h in enumerate(headers):
                if h:
                    header_map[h.strip()] = idx

            required_fields = ['题干', '选项A', '选项B', '选项C', '选项D', '答案', '题型']
            for field in required_fields:
                if field not in header_map:
                    # 先关闭工作簿再返回错误
                    if wb:
                        wb.close()
                    return jsonify({'status': 'error', 'message': f'Missing required column: {field}'}), 400

            # 处理Excel换行符的函数
            def process_value(value):
                if value is None:
                    return ''
                s = str(value)
                # Excel中的换行符通常是 \n，但有时会是 \r\n
                # 也需要处理单元格内部的换行符
                s = s.replace('\r\n', '\n').replace('\r', '\n')
                return s

            # 将换行符转换为HTML的函数，允许安全的HTML标签
            def to_html(value):
                if not value:
                    return ''
                s = str(value)
                
                import re
                
                # 允许的标签列表（不区分大小写）
                allowed_tags = ['img', 'br', 'p', 'div', 'span', 'strong', 'em', 
                               'b', 'i', 'u', 'ul', 'ol', 'li', 'table', 'tr', 
                               'td', 'th', 'tbody', 'thead', 'h1', 'h2', 'h3', 
                               'h4', 'h5', 'h6', 'a', 'pre', 'code', 'hr', 'sub', 'sup']
                
                # 分两步处理：先标记允许的标签，再转义其他字符
                # 第一步：找出所有标签并暂时替换为占位符
                placeholder_map = {}
                placeholder_counter = 0
                
                # 匹配标签的正则表达式
                tag_regex = re.compile(r'</?(\w+)[^>]*>', re.IGNORECASE)
                
                def tag_replacer(match):
                    nonlocal placeholder_counter
                    tag = match.group(1).lower()
                    if tag in allowed_tags:
                        placeholder = f'__SAFE_TAG_{placeholder_counter}__'
                        placeholder_map[placeholder] = match.group(0)
                        placeholder_counter += 1
                        return placeholder
                    else:
                        # 非允许标签则转义
                        return f'&lt;{match.group(0)[1:-1]}&gt;'
                
                # 替换所有标签为占位符
                s = tag_regex.sub(tag_replacer, s)
                
                # 第二步：转义其他HTML特殊字符
                s = s.replace('&', '&amp;').replace('"', '&quot;').replace("'", '&#39;')
                
                # 注意：我们已经通过占位符处理了<和>
                
                # 第三步：处理换行符
                s = s.replace('\n', '<br>')
                
                # 第四步：恢复安全标签
                for placeholder, original_tag in placeholder_map.items():
                    s = s.replace(placeholder, original_tag)
                
                return s

            success_count = 0
            error_rows = []
            duplicate_count = 0

            for row_num, row in enumerate(ws.iter_rows(min_row=2), start=2):
                if all(cell.value is None for cell in row):
                    continue

                try:
                    stem = process_value(row[header_map['题干']].value)
                    if not stem or str(stem).strip() == '':
                        error_rows.append({'row': row_num, 'error': '题干为空'})
                        continue

                    option_a = process_value(row[header_map['选项A']].value)
                    option_b = process_value(row[header_map['选项B']].value)
                    option_c = process_value(row[header_map['选项C']].value)
                    option_d = process_value(row[header_map['选项D']].value)
                    option_e = process_value(row[header_map.get('选项E', -1)].value) if '选项E' in header_map else ''
                    option_f = process_value(row[header_map.get('选项F', -1)].value) if '选项F' in header_map else ''
                    answer = str(row[header_map['答案']].value or '').upper()
                    explanation = process_value(row[header_map.get('解析', -1)].value) if '解析' in header_map else ''
                    question_type_name = row[header_map.get('题型', -1)].value if '题型' in header_map else ''

                    answer_clean = ''.join(c for c in answer if c in 'ABCDEF')
                    if not answer_clean:
                        error_rows.append({'row': row_num, 'error': '答案格式错误'})
                        continue

                    chapter_name = row[header_map.get('章节', -1)].value if '章节' in header_map else ''
                    chapter_id = None
                    if chapter_name:
                        chapter = Chapter.query.filter_by(name=chapter_name).first()
                        if chapter:
                            chapter_id = chapter.id

                    existing = Question.query.filter_by(stem=stem).first()
                    if existing:
                        if duplicate_handling == 'skip':
                            duplicate_count += 1
                            continue
                        elif duplicate_handling == '覆盖':
                            existing.option_a = option_a
                            existing.option_b = option_b
                            existing.option_c = option_c
                            existing.option_d = option_d
                            existing.option_e = option_e
                            existing.option_f = option_f
                            existing.answer = answer_clean
                            existing.explanation = explanation
                            # 同时更新HTML版本
                            existing.stem_html = to_html(stem)
                            existing.option_a_html = to_html(option_a)
                            existing.option_b_html = to_html(option_b)
                            existing.option_c_html = to_html(option_c)
                            existing.option_d_html = to_html(option_d)
                            existing.option_e_html = to_html(option_e)
                            existing.option_f_html = to_html(option_f)
                            existing.explanation_html = to_html(explanation)
                            if chapter_id:
                                existing.chapter_id = chapter_id
                            db.session.commit()
                            success_count += 1
                            continue
                        elif duplicate_handling == 'import_all':
                            # import_all模式：即使重复也创建新题目
                            pass

                    qtype = QuestionType.query.filter_by(name=question_type_name).first()
                    if not qtype:
                        qtype = QuestionType.query.first()

                    question = Question(
                        stem=stem,
                        option_a=option_a,
                        option_b=option_b,
                        option_c=option_c,
                        option_d=option_d,
                        option_e=option_e,
                        option_f=option_f,
                        answer=answer_clean,
                        explanation=explanation,
                        # 添加HTML版本，处理换行符
                        stem_html=to_html(stem),
                        option_a_html=to_html(option_a),
                        option_b_html=to_html(option_b),
                        option_c_html=to_html(option_c),
                        option_d_html=to_html(option_d),
                        option_e_html=to_html(option_e),
                        option_f_html=to_html(option_f),
                        explanation_html=to_html(explanation),
                        question_type_id=qtype.id if qtype else None,
                        chapter_id=chapter_id,
                        status='published'
                    )
                    db.session.add(question)
                    success_count += 1

                except Exception as e:
                    error_rows.append({'row': row_num, 'error': str(e)})

            db.session.commit()
            print(f"导入完成: 成功 {success_count} 条, 跳过 {duplicate_count} 条, 错误 {len(error_rows)} 条")
            log_operation('admin', 'import_questions', 'batch', None, f'Imported {success_count} questions, {duplicate_count} duplicates, {len(error_rows)} errors')

            # 先关闭工作簿
            if wb:
                wb.close()

            response = jsonify({
                'status': 'ok',
                'message': f'Import completed',
                'data': {
                    'success_count': success_count,
                    'duplicate_count': duplicate_count,
                    'error_count': len(error_rows),
                    'error_rows': error_rows[:100]
                }
            })
            print("返回响应:", response.get_json())
            return response, 200

        except Exception as e:
            db.session.rollback()
            print(f"导入处理异常: {str(e)}")
            import traceback
            traceback.print_exc()
            # 确保关闭工作簿
            if wb:
                try:
                    wb.close()
                except:
                    pass
            return jsonify({'status': 'error', 'message': f'Import failed: {str(e)}'}), 500
        finally:
            # 延迟删除文件，避免被占用
            if os.path.exists(filepath):
                print(f"准备删除临时文件: {filepath}")
                try:
                    import time
                    time.sleep(0.1)  # 短暂延迟
                    os.remove(filepath)
                    print(f"临时文件已删除")
                except Exception as e:
                    print(f"删除临时文件失败: {str(e)}")
    except Exception as e:
        print(f"服务器异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/export/questions', methods=['POST'])
def export_questions():
    data = request.json
    question_ids = data.get('question_ids', [])

    if question_ids:
        questions = Question.query.filter(Question.id.in_(question_ids)).all()
    else:
        questions = Question.query.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "题目导出"

    headers = ['题干', '选项A', '选项B', '选项C', '选项D', '选项E', '选项F', '答案', '解析', '题型', '章节', '难度', '状态']
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)

    for row_num, q in enumerate(questions, 2):
        ws.cell(row=row_num, column=1, value=q.stem)
        ws.cell(row=row_num, column=2, value=q.option_a)
        ws.cell(row=row_num, column=3, value=q.option_b)
        ws.cell(row=row_num, column=4, value=q.option_c)
        ws.cell(row=row_num, column=5, value=q.option_d)
        ws.cell(row=row_num, column=6, value=q.option_e)
        ws.cell(row=row_num, column=7, value=q.option_f)
        ws.cell(row=row_num, column=8, value=q.answer)
        ws.cell(row=row_num, column=9, value=q.explanation)
        ws.cell(row=row_num, column=10, value=q.question_type.name if q.question_type else '')
        ws.cell(row=row_num, column=11, value=q.chapter.name if q.chapter else '')
        ws.cell(row=row_num, column=12, value=q.difficulty)
        ws.cell(row=row_num, column=13, value=q.status)

    export_path = os.path.join(app.config['UPLOAD_FOLDER'], 'exported_questions.xlsx')
    wb.save(export_path)
    return send_file(export_path, as_attachment=True, download_name='exported_questions.xlsx')

@app.route('/api/practice/memorize', methods=['GET'])
def practice_memorize():
    chapter_id = request.args.get('chapter_id', type=int)
    question_type_id = request.args.get('question_type_id', type=int)

    query = Question.query.filter_by(status='published')
    if chapter_id:
        query = query.filter_by(chapter_id=chapter_id)
    if question_type_id:
        query = query.filter_by(question_type_id=question_type_id)

    questions = query.order_by(Question.id).all()
    return jsonify({
        'status': 'ok',
        'data': [q.to_dict() for q in questions],
        'total': len(questions)
    })

@app.route('/api/practice/sequential', methods=['POST'])
def practice_sequential():
    data = request.json
    chapter_ids = data.get('chapter_ids', [])
    question_type_id = data.get('question_type_id')
    shuffle_options = data.get('shuffle_options', False)

    query = Question.query.filter_by(status='published')
    if chapter_ids:
        query = query.filter(Question.chapter_id.in_(chapter_ids))
    if question_type_id:
        query = query.filter_by(question_type_id=question_type_id)

    questions = query.order_by(Question.id).all()
    result = []
    for q in questions:
        q_dict = q.to_dict(shuffle_options=shuffle_options)
        result.append(q_dict)

    session_id = str(uuid.uuid4())
    return jsonify({
        'status': 'ok',
        'data': result,
        'session_id': session_id
    })

@app.route('/api/practice/random', methods=['POST'])
def practice_random():
    data = request.json
    count = data.get('count', 10)
    score = data.get('score', 5)
    shuffle_options = data.get('shuffle_options', True)
    chapter_ids = data.get('chapter_ids', [])
    chapter_ratios = data.get('chapter_ratios', {})
    wrong_ratio = data.get('wrong_ratio', 0)
    user_id = data.get('user_id', 'default_user')
    question_type_id = data.get('question_type_id')

    selected = []
    selected_ids = set()

    # 获取错题本中的易错题（错误次数>2）
    wrong_question_ids = []
    if wrong_ratio > 0:
        wrong_query = db.session.query(
            WrongQuestion.question_id,
            db.func.count(WrongQuestion.id).label('wrong_count')
        ).filter(
            WrongQuestion.user_id == user_id
        ).group_by(
            WrongQuestion.question_id
        ).having(
            db.func.count(WrongQuestion.id) > 2
        ).subquery()
        wrong_question_ids = [wq.question_id for wq in db.session.query(wrong_query).all()]

    # 判断是否设置了章节抽题比例
    has_chapter_ratios = any(chapter_ratios.get(cid, 0) > 0 for cid in chapter_ids) if chapter_ids else False

    # 计算各章节的抽题数量
    chapter_totals = {}
    if chapter_ids:
        if has_chapter_ratios:
            # 情况一：部分或全部章节设置了比例
            final_chapter_ratios = {}
            set_chapters = [cid for cid in chapter_ids if chapter_ratios.get(cid, 0) > 0]
            unset_chapters = [cid for cid in chapter_ids if chapter_ratios.get(cid, 0) == 0]

            # 设置过比例的章节
            for cid in set_chapters:
                final_chapter_ratios[cid] = chapter_ratios[cid]

            # 未设置比例的章节平均分配剩余比例
            if unset_chapters:
                remaining = 100 - sum(final_chapter_ratios.values())
                if remaining > 0:
                    each_ratio = int(remaining / len(unset_chapters))
                    for i, cid in enumerate(unset_chapters):
                        if i == len(unset_chapters) - 1:
                            final_chapter_ratios[cid] = remaining - each_ratio * (len(unset_chapters) - 1)
                        else:
                            final_chapter_ratios[cid] = each_ratio

            # 计算各章节抽题数量
            for cid in chapter_ids:
                chapter_totals[cid] = int(count * final_chapter_ratios.get(cid, 0) / 100)
        else:
            # 情况二：都没设置比例，不分配具体章节数量，最后统一从选中章节随机抽取
            pass
    else:
        # 没有选中章节，从全部题库抽取
        pass

    # 获取所有可选题目的基础查询
    base_query = Question.query.filter_by(status='published')
    if question_type_id:
        base_query = base_query.filter_by(question_type_id=question_type_id)

    # 开始抽题
    if chapter_ids:
        if has_chapter_ratios:
            # 按章节比例抽题
            for chapter_id in chapter_ids:
                chapter_total = chapter_totals.get(chapter_id, 0)
                if chapter_total <= 0:
                    continue

                # 获取该章节的题目
                chapter_questions = base_query.filter_by(chapter_id=chapter_id).all()
                if not chapter_questions:
                    continue

                # 从该章节抽取题目
                chapter_selected = []

                # 1. 先从该章节抽易错题（如果设置了易错题比例）
                if wrong_ratio > 0:
                    chapter_wrong_count = int(chapter_total * wrong_ratio / 100)
                    if chapter_wrong_count > 0:
                        chapter_wrong_questions = [
                            q for q in chapter_questions
                            if q.id in wrong_question_ids and q.id not in selected_ids
                        ]
                        if chapter_wrong_questions:
                            take = min(chapter_wrong_count, len(chapter_wrong_questions))
                            chapter_selected.extend(random.sample(chapter_wrong_questions, take))

                # 2. 用该章节普通题目补足
                remaining = chapter_total - len(chapter_selected)
                if remaining > 0:
                    chapter_normal_questions = [
                        q for q in chapter_questions
                        if q.id not in selected_ids and q not in chapter_selected
                    ]
                    if chapter_normal_questions:
                        take = min(remaining, len(chapter_normal_questions))
                        chapter_selected.extend(random.sample(chapter_normal_questions, take))

                selected.extend(chapter_selected)
                selected_ids.update(q.id for q in chapter_selected)
        else:
            # 没有设置章节比例，统一从选中章节抽题
            # 获取所有选中章节的题目
            all_chapter_questions = base_query.filter(Question.chapter_id.in_(chapter_ids)).all()
            if not all_chapter_questions:
                pass
            else:
                # 1. 先抽易错题
                if wrong_ratio > 0:
                    wrong_count = int(count * wrong_ratio / 100)
                    chapter_wrong_questions = [
                        q for q in all_chapter_questions
                        if q.id in wrong_question_ids and q.id not in selected_ids
                    ]
                    if chapter_wrong_questions:
                        take = min(wrong_count, len(chapter_wrong_questions))
                        selected.extend(random.sample(chapter_wrong_questions, take))
                        selected_ids.update(q.id for q in selected)

                # 2. 用普通题目补足
                remaining = count - len(selected)
                if remaining > 0:
                    available_normal = [
                        q for q in all_chapter_questions
                        if q.id not in selected_ids
                    ]
                    if available_normal:
                        take = min(remaining, len(available_normal))
                        selected.extend(random.sample(available_normal, take))

        # 如果从章节抽取后总数量不足，从选中章节中继续补足
        if len(selected) < count:
            remaining = count - len(selected)
            all_chapter_questions = base_query.filter(Question.chapter_id.in_(chapter_ids)).all()
            remaining_questions = [q for q in all_chapter_questions if q.id not in selected_ids]

            if remaining_questions:
                take = min(remaining, len(remaining_questions))
                selected.extend(random.sample(remaining_questions, take))
    else:
        # 没有选中章节，从全部题库抽取
        all_questions = base_query.all()

        # 1. 先抽易错题
        if wrong_ratio > 0:
            wrong_count = int(count * wrong_ratio / 100)
            available_wrong = [q for q in all_questions if q.id in wrong_question_ids and q.id not in selected_ids]
            if available_wrong:
                take = min(wrong_count, len(available_wrong))
                selected.extend(random.sample(available_wrong, take))
                selected_ids.update(q.id for q in selected)

        # 2. 用普通题目补足
        remaining = count - len(selected)
        if remaining > 0:
            available_normal = [q for q in all_questions if q.id not in selected_ids]
            if available_normal:
                take = min(remaining, len(available_normal))
                selected.extend(random.sample(available_normal, take))

    # 打乱最终结果
    random.shuffle(selected)

    # 构建返回结果
    result = []
    for q in selected[:count]:
        q_dict = q.to_dict(shuffle_options=shuffle_options)
        q_dict['score'] = score
        result.append(q_dict)

    session_id = str(uuid.uuid4())
    return jsonify({
        'status': 'ok',
        'data': result,
        'session_id': session_id,
        'total': len(result)
    })

@app.route('/api/wrong-questions', methods=['GET', 'POST'])
def handle_wrong_questions():
    user_id = request.args.get('user_id', 'default_user')

    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        question_type_id = request.args.get('question_type_id', type=int)
        chapter_id = request.args.get('chapter_id', type=int)
        wrong_count_eq = request.args.get('wrong_count_eq', type=int)
        min_reappearance_count = request.args.get('min_reappearance_count', type=int)

        query = WrongQuestion.query.filter_by(user_id=user_id)
        if question_type_id:
            query = query.join(Question).filter(Question.question_type_id == question_type_id)
        if chapter_id:
            query = query.join(Question).filter(Question.chapter_id == chapter_id)
        if wrong_count_eq is not None:
            if wrong_count_eq == 1:
                query = query.filter(WrongQuestion.wrong_count == 1)
            elif wrong_count_eq == 2:
                query = query.filter(WrongQuestion.wrong_count == 2)
            elif wrong_count_eq == 3:
                query = query.filter(WrongQuestion.wrong_count == 3)
            elif wrong_count_eq == 4:
                query = query.filter(WrongQuestion.wrong_count > 3)
            elif wrong_count_eq == 5:
                query = query.filter(WrongQuestion.wrong_count == 4)
            elif wrong_count_eq == 6:
                query = query.filter(WrongQuestion.wrong_count == 5)
            elif wrong_count_eq == 7:
                query = query.filter(WrongQuestion.wrong_count > 5)
            else:
                query = query.filter(WrongQuestion.wrong_count == wrong_count_eq)
        if min_reappearance_count is not None:
            query = query.filter(WrongQuestion.reappearance_count >= min_reappearance_count)

        pagination = query.order_by(WrongQuestion.last_wrong_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'status': 'ok',
            'data': [wq.to_dict() for wq in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    else:
        data = request.json
        question_id = data.get('question_id')
        wrong_q = WrongQuestion(
            user_id=user_id,
            question_id=question_id
        )
        db.session.add(wrong_q)
        db.session.commit()
        return jsonify({'status': 'ok', 'data': wrong_q.to_dict()})

@app.route('/api/wrong-questions/<int:wrong_id>', methods=['DELETE'])
def delete_wrong_question(wrong_id):
    wrong_q = WrongQuestion.query.get_or_404(wrong_id)
    db.session.delete(wrong_q)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': 'Removed from wrong questions'})

@app.route('/api/wrong-questions/clear', methods=['DELETE'])
def clear_wrong_questions():
    user_id = request.args.get('user_id', 'default_user')
    WrongQuestion.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({'status': 'ok', 'message': 'Cleared all wrong questions'})

@app.route('/api/wrong-questions/batch', methods=['DELETE'])
def batch_remove_wrong_questions():
    user_id = request.json.get('user_id', 'default_user')
    wrong_ids = request.json.get('wrong_ids', [])
    
    if not wrong_ids:
        return jsonify({'status': 'error', 'message': 'No wrong question IDs provided'}), 400
    
    deleted_count = WrongQuestion.query.filter(
        WrongQuestion.user_id == user_id,
        WrongQuestion.id.in_(wrong_ids)
    ).delete(synchronize_session=False)
    
    db.session.commit()
    return jsonify({
        'status': 'ok', 
        'message': f'Removed {deleted_count} questions from wrong questions book'
    })

@app.route('/api/wrong-questions/practice', methods=['POST'])
def practice_wrong_questions():
    user_id = request.json.get('user_id', 'default_user')
    shuffle = request.json.get('shuffle', True)
    shuffle_options = request.json.get('shuffle_options', True)
    chapter_ids = request.json.get('chapter_ids', [])
    wrong_ids = request.json.get('wrong_ids', [])
    
    print(f"DEBUG - user_id: {user_id}")
    print(f"DEBUG - chapter_ids: {chapter_ids}")
    print(f"DEBUG - wrong_ids: {wrong_ids}")
    print(f"DEBUG - shuffle_options: {shuffle_options}")

    query = WrongQuestion.query.filter_by(user_id=user_id)
    
    if chapter_ids and len(chapter_ids) > 0:
        print(f"DEBUG - Filtering by chapters: {chapter_ids}")
        query = query.join(Question).filter(Question.chapter_id.in_(chapter_ids))
    
    if wrong_ids and len(wrong_ids) > 0:
        print(f"DEBUG - Filtering by wrong_ids: {wrong_ids}")
        query = query.filter(WrongQuestion.id.in_(wrong_ids))
    
    wrong_questions = query.all()
    print(f"DEBUG - Found {len(wrong_questions)} wrong questions")
    
    if not wrong_questions:
        return jsonify({'status': 'ok', 'data': [], 'session_id': str(uuid.uuid4())})

    for wq in wrong_questions:
        wq.reappearance_count += 1
    db.session.commit()

    questions = [wq.question for wq in wrong_questions if wq.question]
    if shuffle:
        random.shuffle(questions)

    result = []
    for q in questions:
        q_dict = q.to_dict(shuffle_options=shuffle_options)
        result.append(q_dict)

    session_id = str(uuid.uuid4())
    return jsonify({
        'status': 'ok',
        'data': result,
        'session_id': session_id
    })

@app.route('/api/favorites', methods=['GET', 'POST'])
def handle_favorites():
    user_id = request.args.get('user_id', 'default_user')

    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        pagination = FavoriteQuestion.query.filter_by(user_id=user_id).order_by(
            FavoriteQuestion.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'status': 'ok',
            'data': [f.to_dict() for f in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    else:
        data = request.json
        question_id = data.get('question_id')

        existing = FavoriteQuestion.query.filter_by(user_id=user_id, question_id=question_id).first()
        if existing:
            return jsonify({'status': 'ok', 'data': existing.to_dict(), 'message': 'Already favorited'})

        favorite = FavoriteQuestion(
            user_id=user_id,
            question_id=question_id
        )
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'status': 'ok', 'data': favorite.to_dict()})

@app.route('/api/favorites/<int:favorite_id>', methods=['DELETE'])
def delete_favorite(favorite_id):
    favorite = FavoriteQuestion.query.get_or_404(favorite_id)
    db.session.delete(favorite)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': 'Removed from favorites'})

@app.route('/api/favorites/check/<int:question_id>', methods=['GET'])
def check_favorite(question_id):
    user_id = request.args.get('user_id', 'default_user')
    favorite = FavoriteQuestion.query.filter_by(user_id=user_id, question_id=question_id).first()
    return jsonify({'status': 'ok', 'is_favorite': favorite is not None})

@app.route('/api/answers', methods=['POST'])
def submit_answer():
    data = request.json
    session_id = data.get('session_id', 'default')
    question_id = data.get('question_id')
    user_answer = data.get('answer', '').upper()
    user_id = data.get('user_id', 'default_user')
    expected_answer = data.get('expected_answer')

    question = Question.query.get_or_404(question_id)
    if expected_answer is not None and expected_answer != '':
        correct_answer = expected_answer.upper()
    else:
        correct_answer = question.answer.upper()
    is_correct = user_answer == correct_answer

    answer = UserAnswer(
        session_id=session_id,
        question_id=question_id,
        user_answer=user_answer,
        is_correct=is_correct
    )
    db.session.add(answer)

    if not is_correct:
        wrong_q = WrongQuestion.query.filter_by(user_id=user_id, question_id=question_id).first()
        if wrong_q:
            wrong_q.wrong_count += 1
            wrong_q.last_wrong_at = datetime.utcnow()
        else:
            wrong_q = WrongQuestion(
                user_id=user_id,
                question_id=question_id
            )
            db.session.add(wrong_q)

    db.session.commit()

    return jsonify({
        'status': 'ok',
        'data': {
            'is_correct': is_correct,
            'correct_answer': correct_answer,
            'explanation': question.explanation,
            'explanation_html': question.explanation_html
        }
    })

@app.route('/api/answers/history/<int:question_id>', methods=['GET'])
def get_answer_history(question_id):
    user_id = request.args.get('user_id', 'default_user')
    answers = UserAnswer.query.filter_by(session_id=user_id, question_id=question_id).order_by(
        UserAnswer.answered_at.desc()
    ).limit(10).all()
    return jsonify({
        'status': 'ok',
        'data': [a.to_dict() for a in answers]
    })

@app.route('/api/preferences', methods=['GET', 'PUT'])
def handle_preferences():
    user_id = request.args.get('user_id', 'default_user')

    pref = UserPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        pref = UserPreference(user_id=user_id)
        db.session.add(pref)
        db.session.commit()

    if request.method == 'GET':
        return jsonify({'status': 'ok', 'data': pref.to_dict()})
    else:
        data = request.json
        pref.eye_protection_mode = data.get('eye_protection_mode', pref.eye_protection_mode)
        pref.font_size = data.get('font_size', pref.font_size)
        pref.font_family = data.get('font_family', pref.font_family)
        db.session.commit()
        return jsonify({'status': 'ok', 'data': pref.to_dict()})

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    user_id = request.args.get('user_id', 'default_user')

    total_questions = Question.query.filter_by(status='published').count()
    total_answered = UserAnswer.query.filter_by(session_id=user_id).count()
    total_correct = UserAnswer.query.filter_by(session_id=user_id, is_correct=True).count()
    correct_rate = (total_correct / total_answered * 100) if total_answered > 0 else 0

    wrong_count = WrongQuestion.query.filter_by(user_id=user_id).count()
    favorite_count = FavoriteQuestion.query.filter_by(user_id=user_id).count()

    type_stats = db.session.query(
        Question.question_type_id,
        QuestionType.name,
        db.func.count(Question.id).label('count')
    ).join(QuestionType).group_by(Question.question_type_id).all()

    return jsonify({
        'status': 'ok',
        'data': {
            'total_questions': total_questions,
            'total_answered': total_answered,
            'total_correct': total_correct,
            'correct_rate': round(correct_rate, 2),
            'wrong_count': wrong_count,
            'favorite_count': favorite_count,
            'type_stats': [{'type_id': t[0], 'type_name': t[1], 'count': t[2]} for t in type_stats]
        }
    })

@app.route('/api/logs', methods=['GET'])
def get_operation_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    pagination = OperationLog.query.order_by(OperationLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'status': 'ok',
        'data': [log.to_dict() for log in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if QuestionType.query.count() == 0:
            default_types = [
                QuestionType(name='单选题', is_multiple=False),
                QuestionType(name='多选题', is_multiple=True),
                QuestionType(name='判断题', is_multiple=False)
            ]
            db.session.add_all(default_types)
        if Chapter.query.count() == 0:
            default_chapter = Chapter(name='默认章节', order=0)
            db.session.add(default_chapter)
        if UserPreference.query.count() == 0:
            default_pref = UserPreference(user_id='default_user')
            db.session.add(default_pref)
        db.session.commit()

    app.run(debug=False, host='0.0.0.0', port=5000)
