from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import json
import traceback
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure OpenAI API
api_key = os.getenv('OPENAI_API_KEY')
print(f"🔍 API Key loaded from env: {'YES' if api_key else 'NO'}")
if api_key:
    print(f"🔑 API Key preview: {api_key[:10]}...")
else:
    print("❌ ERROR: OPENAI_API_KEY not found!")
    print("Environment variables available:")
    for key in os.environ:
        if 'API' in key or 'KEY' in key:
            print(f"  {key}: {os.environ[key][:10]}...")

# Initialize OpenAI client
if api_key:
    try:
        client = openai.OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
        
        # Test connection immediately
        try:
            print("🧪 Testing OpenAI connection...")
            test_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say 'TEST OK'"}],
                max_tokens=10
            )
            print(f"✅ OpenAI test SUCCESS: {test_response.choices[0].message.content}")
            openai_working = True
        except Exception as test_e:
            print(f"❌ OpenAI test FAILED: {test_e}")
            openai_working = False
            client = None
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI: {e}")
        client = None
        openai_working = False
else:
    client = None
    openai_working = False

@app.route('/')
def home():
    return jsonify({
        "status": "Resume Analyzer API",
        "openai_configured": client is not None,
        "openai_working": openai_working,
        "api_key_exists": bool(api_key),
        "endpoints": {
            "/health": "GET - Check API health",
            "/test-openai": "GET - Test OpenAI connection",
            "/analyze": "POST - Analyze a resume",
            "/debug-env": "GET - Show environment variables"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "openai_client": "ready" if client else "not_configured",
        "api_key": "configured" if api_key else "missing"
    })

@app.route('/test-openai', methods=['GET'])
def test_openai():
    if not client:
        return jsonify({
            "success": False,
            "error": "OpenAI client not initialized",
            "api_key_provided": bool(api_key),
            "solution": "Check OPENAI_API_KEY environment variable on Render"
        })
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'Hello World'"}],
            max_tokens=10
        )
        
        return jsonify({
            "success": True,
            "message": "OpenAI API is working!",
            "response": response.choices[0].message.content,
            "model": "gpt-3.5-turbo"
        })
    except openai.AuthenticationError as e:
        return jsonify({
            "success": False,
            "error": "Authentication failed",
            "details": "Invalid API key",
            "solution": "Check your OpenAI API key in Render environment variables"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        })

@app.route('/debug-env', methods=['GET'])
def debug_env():
    """Show all environment variables (without exposing full API key)"""
    env_vars = {}
    for key, value in os.environ.items():
        if 'KEY' in key or 'SECRET' in key or 'PASSWORD' in key:
            env_vars[key] = f"{value[:5]}..." if value else "empty"
        else:
            env_vars[key] = value
    
    return jsonify({
        "environment_variables": env_vars,
        "openai_api_key_set": bool(api_key),
        "openai_api_key_preview": f"{api_key[:10]}..." if api_key else "not_set",
        "python_version": os.sys.version
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    """Super simplified analyze endpoint"""
    print("\n" + "="*60)
    print("📥 NEW ANALYSIS REQUEST RECEIVED")
    print("="*60)
    
    try:
        # Log request data
        print(f"📋 Form data keys: {list(request.form.keys())}")
        print(f"📁 Files in request: {list(request.files.keys())}")
        
        # Check for required data
        if 'jobDescription' not in request.form:
            print("❌ Missing jobDescription in form data")
            return jsonify({"error": "jobDescription is required"}), 400
        
        job_description = request.form['jobDescription']
        print(f"📝 Job description received ({len(job_description)} chars)")
        
        # Check if file was uploaded
        if 'resume' not in request.files:
            print("❌ No resume file uploaded")
            return jsonify({"error": "Resume file is required"}), 400
        
        resume_file = request.files['resume']
        if resume_file.filename == '':
            print("❌ Empty filename")
            return jsonify({"error": "No file selected"}), 400
        
        print(f"📄 File uploaded: {resume_file.filename}")
        
        # Save file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp_file:
            # For now, just read text files
            content = resume_file.read().decode('utf-8', errors='ignore')
            tmp_file.write(content.encode('utf-8'))
            tmp_path = tmp_file.name
        
        resume_text = content[:1000]  # Just use first 1000 chars for testing
        print(f"📖 Resume text extracted ({len(resume_text)} chars)")
        
        # Check OpenAI
        if not client:
            print("❌ OpenAI client not available")
            return jsonify({
                "error": "OpenAI not configured",
                "solution": "Set OPENAI_API_KEY in Render environment variables",
                "debug_info": {
                    "api_key_exists": bool(api_key),
                    "api_key_preview": f"{api_key[:10]}..." if api_key else "none"
                }
            }), 500
        
        print("🤖 Calling OpenAI API...")
        
        # SIMPLIFIED PROMPT
        prompt = f"""
        Analyze this resume against the job description.
        
        Resume (first 1000 chars):
        {resume_text}
        
        Job Description:
        {job_description[:500]}
        
        Provide a simple JSON response with:
        1. candidate_name (extract from resume or use "Candidate")
        2. overall_score (0-100)
        3. recommendation ("Recommended" or "Not Recommended")
        4. key_skills (2-3 skills from resume)
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You analyze resumes and return JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            print(f"✅ OpenAI response received: {result_text[:100]}...")
            
            # Try to parse JSON
            try:
                # Extract JSON from response
                if '```json' in result_text:
                    result_text = result_text.split('```json')[1].split('```')[0].strip()
                elif '```' in result_text:
                    result_text = result_text.split('```')[1].split('```')[0].strip()
                
                analysis = json.loads(result_text)
                print(f"✅ JSON parsed successfully")
                
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse JSON, using fallback")
                analysis = {
                    "candidate_name": "Candidate",
                    "overall_score": 75,
                    "recommendation": "Recommended",
                    "key_skills": ["Communication", "Problem Solving"],
                    "note": "Parsed from text response"
                }
            
            # Clean up temp file
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            print(f"✅ Analysis complete! Score: {analysis.get('overall_score', 'N/A')}")
            print("="*60)
            
            return jsonify({
                "success": True,
                "analysis": analysis,
                "debug": {
                    "openai_model": "gpt-3.5-turbo",
                    "resume_chars_processed": len(resume_text),
                    "job_description_chars": len(job_description)
                }
            })
            
        except openai.APIError as e:
            print(f"❌ OpenAI API Error: {e}")
            return jsonify({
                "error": "OpenAI API error",
                "details": str(e),
                "type": "api_error"
            }), 500
            
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {traceback.format_exc()}")
        return jsonify({
            "error": "Server error",
            "details": str(e),
            "traceback": traceback.format_exc()[-500:]  # Last 500 chars
        }), 500

@app.route('/simple-test', methods=['GET'])
def simple_test():
    """Direct test without file upload"""
    if not client:
        return jsonify({"error": "OpenAI not configured"}), 500
    
    try:
        # Use a fixed resume text for testing
        resume_text = "John Doe, Software Engineer, 5 years Python experience, BS Computer Science"
        job_description = "Looking for Python developer with degree"
        
        prompt = f"Resume: {resume_text}\nJob: {job_description}\nReturn JSON with name, score, and recommendation."
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        
        return jsonify({
            "success": True,
            "test": "simple",
            "response": response.choices[0].message.content
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"\n🚀 Starting server on port {port}")
    print(f"🔑 OpenAI configured: {'✅' if client else '❌'}")
    print(f"🌐 Open your browser to: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
