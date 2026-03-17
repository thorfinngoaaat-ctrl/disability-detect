from django.shortcuts import render, HttpResponse, redirect
from . import models

def index(request):
    return render(request, 'index.html')

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email    = request.POST.get('email')
        password = request.POST.get('password')
        if models.User.objects.filter(email=email).exists():
            return HttpResponse("Email already registered")
        user = models.User(username=username, email=email, password=password)
        user.save()
        return redirect('login')
    return render(request, 'register.html')

def home(request):
    if 'email' not in request.session:
        return redirect('login')
    return render(request, 'home.html')

def login(request):
    if request.method == 'POST':
        email    = request.POST.get('email')
        password = request.POST.get('password')
        user     = models.User.objects.filter(email=email, password=password)
        if user:
            request.session['email'] = email
            return redirect('home')
        else:
            return HttpResponse("Invalid email or password")
    return render(request, 'login.html')

def profile(request):
    user = models.User.objects.filter(email=request.session['email']).first()
    if not user:
        return redirect('login')
    return render(request, 'profile.html', {'user': user})

def logout(request):
    request.session.flush()
    return redirect('index')

def test(request):
    if 'email' not in request.session:
        return redirect('login')
    return render(request, 'test.html')

def typetest(request):
    return render(request, 'typetest.html')

def focustest(request):
    return render(request, 'focustest.html')

def autism(request):
    return render(request, 'autism.html')

import random

def math(request):
    if 'email' not in request.session:
        return redirect('login')
    questions = []
    for _ in range(10):
        operation = random.choice(['+', '-', '*'])
        if operation == '*':
            a, b   = random.randint(2, 12), random.randint(2, 10)
            answer = a * b
        elif operation == '+':
            a, b   = random.randint(5, 20), random.randint(5, 20)
            answer = a + b
        else:
            a, b   = random.randint(10, 20), random.randint(2, 10)
            if a < b: a, b = b, a
            answer = a - b
        questions.append({'q': f"{a} {operation.replace('*','x')} {b}", 'a': answer})
    return render(request, 'math.html', {'questions': questions})


import requests
import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import User, TypingResult, ScreeningResult, AttentionResult, AutismResult

@csrf_exempt
@require_POST
def call_llm(request):
    try:
        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({'error': 'Unauthorized: No user session found'}, status=401)

        target_user = models.User.objects.get(email=user_email)

        typing    = TypingResult.objects.filter(user=target_user).last()
        screening = ScreeningResult.objects.filter(user=target_user).last()
        attention = AttentionResult.objects.filter(user=target_user).last()
        autism    = AutismResult.objects.filter(user=target_user).last()
        math_res  = models.DyscalculiaResult.objects.filter(user=target_user).last()

        data_lines = []

        if attention:
            attn_acc = round((attention.hits / attention.targets_shown * 100), 1) if attention.targets_shown else 0
            data_lines.append(
                f"ATTENTION: accuracy={attn_acc}%, omissions={attention.omissions}, "
                f"commissions={attention.commissions}, avg_rt={attention.avg_reaction_time_ms:.0f}ms"
            )

        if screening:
            data_lines.append(
                f"READING: fixations={screening.num_fixations}, "
                f"regression_rate={screening.regression_rate_percent}%, "
                f"avg_fix_duration={screening.avg_fixation_duration_ms:.0f}ms, "
                f"signals=[{screening.signals_detected}]"
            )

        if math_res:
            avg_think = (math_res.total_time_ms - math_res.total_typing_time_ms) / math_res.total_questions
            avg_type  = math_res.total_typing_time_ms / math_res.total_questions
            think_label = (
                "HIGH_FLUENCY"   if avg_think < 4500  else
                "STANDARD"       if avg_think < 8000  else
                "METHODICAL"     if avg_think < 12000 else
                "LABORIOUS"
            )
            data_lines.append(
                f"MATH: accuracy={math_res.accuracy_percent:.1f}%, "
                f"thinking={avg_think:.0f}ms ({think_label}), "
                f"typing={avg_type:.0f}ms, wpm={math_res.typing_wpm:.1f}, "
                f"reversal={math_res.number_reversal_detected}"
            )

        if typing:
            data_lines.append(
                f"TYPING: hold={typing.avg_hold_time_ms:.0f}ms, "
                f"flight={typing.avg_flight_time_ms:.0f}ms, "
                f"effort={typing.effort_score}/100"
            )

        if autism:
            data_lines.append(
                f"AUTISM_TRAITS: match={autism.percentage}%, label={autism.signals}, "
                f"summary=[{autism.summary_text[:120]}]"
            )

        context_data = "\n".join(data_lines) if data_lines else "No test data available yet."

        system_prompt = """You are a cognitive neurodiversity analyst. Given biometric test data, return ONLY a valid JSON object with no extra text.

SCORING RULES (apply strictly, scores 0-100):
- ATTENTION: Start 50. +20 if accuracy>85%. -20 if accuracy<60%. -2 per commission. +10 if avg_rt<400ms. -10 if avg_rt>600ms.
- READING: Start 50. -20 if regression_rate>25%. +15 if regression_rate<10%. -10 if fixations>80. +10 if fixations<40.
- MATH: Start 50. +25 if accuracy=100%. +10 if accuracy>80%. -20 if accuracy<60%. +15 if HIGH_FLUENCY. -15 if LABORIOUS. -10 if reversal=true.
- MOTOR: Start 50. +20 if effort>75. +10 if effort>50. -10 if hold>200ms. -15 if flight>300ms.
- AUTISM: Use the match percentage directly as the score.
- null if module has no data.

BADGE per score: >=75="Strength", >=50="Typical", <50="Needs Review", null="Not Tested"

OVERALL RISK: high if any score<40, medium if any score<60, else low.

Return exactly this JSON:
{
  "summary": "Two sentences max. State the most important finding with actual numbers.",
  "processing_signature": "One sentence describing this person's unique cognitive style.",
  "overall_risk": "low",
  "scores": {
    "attention": 72,
    "reading": 58,
    "math": 85,
    "motor": 60,
    "autism": 34
  },
  "sections": {
    "attention": {
      "badge": "Typical",
      "finding": "One sentence finding.",
      "detail": "One sentence with specific numbers."
    },
    "reading": {
      "badge": "Typical",
      "finding": "One sentence finding.",
      "detail": "One sentence with specific numbers."
    },
    "math": {
      "badge": "Strength",
      "finding": "One sentence finding.",
      "detail": "One sentence with specific numbers."
    },
    "motor": {
      "badge": "Typical",
      "finding": "One sentence finding.",
      "detail": "One sentence with specific numbers."
    },
    "autism": {
      "badge": "Typical",
      "finding": "One sentence finding.",
      "detail": "One sentence with specific numbers."
    }
  }
}"""

        full_prompt = f"DATA:\n{context_data}\n\nReturn only the JSON object."

        url     = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type":  "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": full_prompt}
            ],
            "max_tokens":  600,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        response = requests.post(url, headers=headers, json=payload, timeout=25)

        if response.status_code == 200:
            raw    = response.json()['choices'][0]['message']['content'].strip()
            clean  = raw.replace('```json','').replace('```','').strip()
            parsed = json.loads(clean)
            return JsonResponse({'result': parsed, 'status': 'success'})
        else:
            return JsonResponse({'error': f'Groq API failed: {response.text}'}, status=response.status_code)

    except models.User.DoesNotExist:
        return JsonResponse({'error': 'User record not found'}, status=404)
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'JSON parse error: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


import logging
logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def save_typing_result(request):
    try:
        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({'status': 'error', 'error': 'User not logged in'}, status=401)
        data = json.loads(request.body)
        try:
            target_user = models.User.objects.get(email=user_email)
        except models.User.DoesNotExist:
            return JsonResponse({'status': 'error', 'error': 'User record not found'}, status=404)
        TypingResult.objects.create(
            user=target_user,
            avg_hold_time_ms=data.get('avgHold'),
            avg_flight_time_ms=data.get('avgFlight'),
            hold_variability_ms=data.get('holdVar'),
            flight_variability_ms=data.get('flightVar'),
            effort_score=data.get('effortScore', 0),
            summary_text=data.get('summary', '')
        )
        return JsonResponse({'status': 'success'})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Invalid data format'}, status=400)
    except Exception as e:
        logger.exception("Unexpected error saving typing result")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@require_POST
def save_screening_result(request):
    try:
        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({'status': 'error', 'error': 'No user in session'}, status=401)
        target_user = models.User.objects.get(email=user_email)
        data = json.loads(request.body)
        ScreeningResult.objects.create(
            user=target_user,
            num_fixations=data.get('numFixations'),
            avg_fixation_duration_ms=data.get('avgFixDuration'),
            avg_saccade_length_px=data.get('avgSaccadeLen'),
            regression_rate_percent=data.get('regressionRate'),
            signals_detected=data.get('signals', ''),
            summary_text=data.get('summary', ''),
            raw_gaze_data=data.get('rawData', [])
        )
        return JsonResponse({'status': 'success'})
    except models.User.DoesNotExist:
        return JsonResponse({'status': 'error', 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


def save_attention_test(request):
    user_email = request.session.get('email')
    if not user_email:
        return JsonResponse({'status': 'error', 'message': 'No email in session'}, status=401)
    if request.method == 'POST':
        try:
            data     = json.loads(request.body)
            user_obj = models.User.objects.get(email=user_email)
            new_record = AttentionResult.objects.create(
                user=user_obj,
                hits=data.get('hits', 0),
                omissions=data.get('omissions', 0),
                commissions=data.get('commissions', 0),
                avg_reaction_time_ms=data.get('avg_rt', 0),
                targets_shown=data.get('targets_shown', 0),
                total_trials=data.get('total_trials', 30)
            )
            request.session['attention_results'] = data
            request.session.modified = True
            return JsonResponse({'status': 'success', 'record_id': new_record.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)


@require_POST
def save_autism_result(request):
    try:
        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({'status': 'error', 'error': 'No user in session'}, status=401)
        target_user = models.User.objects.get(email=user_email)
        data = json.loads(request.body)
        models.AutismResult.objects.create(
            user=target_user,
            score=data.get('totalScore'),
            percentage=data.get('percentage'),
            signals=data.get('signals', ''),
            summary_text=data.get('summary', '')
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def save_math_result(request):
    try:
        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({'error': 'Not logged in'}, status=401)
        target_user = models.User.objects.get(email=user_email)
        data      = json.loads(request.body)
        total_q   = data.get('totalQuestions', 0)
        correct   = data.get('correctAnswers', 0)
        avg_time  = data.get('avgResponseTime', 0)
        reversal  = data.get('numberReversal', False)
        accuracy  = (correct / total_q * 100) if total_q > 0 else 0
        signals   = []
        if reversal: signals.append('number_reversal')
        if accuracy < 60 and avg_time > 4000: signals.append('slow_and_inaccurate')
        total_typing = data.get('totalTypingTime', 0)
        total_time   = data.get('totalTime', 0)
        if total_typing > (total_time * 0.6 if total_time else 0):
            signals.append('high_typing_ratio')
        models.DyscalculiaResult.objects.create(
            user=target_user,
            total_questions=total_q,
            correct_answers=correct,
            accuracy_percent=accuracy,
            avg_response_time_ms=avg_time,
            total_time_ms=total_time,
            total_typing_time_ms=total_typing,
            avg_typing_time_ms=data.get('avgTypingTime', 0),
            typing_cpm=data.get('typingCPM', 0),
            typing_wpm=data.get('typingWPM', 0),
            number_reversal_detected=reversal,
            signals_detected=",".join(signals),
            summary_text=data.get('summary', ''),
            raw_responses=data.get('responses', [])
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)