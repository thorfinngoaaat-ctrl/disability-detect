from django.db import models

# Create your models here.
class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    

    def __str__(self):
        return self.username
    
# screener/models.py

from django.db import models # or your custom User if you prefer

class ScreeningResult(models.Model):  # Eye-tracking reading test
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='screening_results')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Core metrics from your analysis function
    num_fixations = models.PositiveIntegerField(null=True, blank=True)
    avg_fixation_duration_ms = models.FloatField(null=True, blank=True)
    avg_saccade_length_px = models.FloatField(null=True, blank=True)
    regression_rate_percent = models.FloatField(null=True, blank=True)
    signals_detected = models.TextField(blank=True)  # e.g. "longer fixations, high regressions"
    
    # Optional: store the raw gaze data or summary text
    raw_gaze_data = models.JSONField(default=dict, blank=True, null=True)
    summary_text = models.TextField(blank=True)
    
    def __str__(self):
        return f"Screening {self.id} - {self.user.username} - {self.created_at.date()}"


class TypingResult(models.Model):  # Typing dynamics test
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='typing_results')
    created_at = models.DateTimeField(auto_now_add=True)
    
    avg_hold_time_ms = models.FloatField(null=True, blank=True)
    avg_flight_time_ms = models.FloatField(null=True, blank=True)
    hold_variability_ms = models.FloatField(null=True, blank=True)
    flight_variability_ms = models.FloatField(null=True, blank=True)
    effort_score = models.PositiveIntegerField(null=True, blank=True)  # your calculated score
    
    summary_text = models.TextField(blank=True)
    
    def __str__(self):
        return f"Typing {self.id} - {self.user.username} - {self.created_at.date()}"


class AutismResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    percentage = models.IntegerField(null=True, blank=True)
    signals = models.CharField(max_length=50, null=True, blank=True) # e.g., "High Likelihood"
    summary_text = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
class AttentionResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attention_results')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Performance Metrics
    hits = models.PositiveIntegerField()          # Correct clicks on A, B, or C
    omissions = models.PositiveIntegerField()     # Missed A, B, or C
    commissions = models.PositiveIntegerField()   # Clicked on wrong letters (Impulsivity)
    avg_reaction_time_ms = models.FloatField()
    
    # Context Metrics (For AI Accuracy Calculation)
    targets_shown = models.PositiveIntegerField(null=True) # How many A, B, or C appeared (e.g., 14)
    total_trials = models.PositiveIntegerField()  # Fixed at 30
    
    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d')}"
    

from django.db import models

class DyscalculiaResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField()
    accuracy_percent = models.FloatField()

    # Timing and Typing metrics
    avg_response_time_ms = models.FloatField()
    total_time_ms = models.FloatField(default=0)
    total_typing_time_ms = models.FloatField(default=0)
    avg_typing_time_ms = models.FloatField(default=0)
    typing_cpm = models.FloatField(default=0)
    typing_wpm = models.FloatField(default=0)

    number_reversal_detected = models.BooleanField(default=False)
    signals_detected = models.TextField(blank=True)

    summary_text = models.TextField()
    raw_responses = models.JSONField(default=list)