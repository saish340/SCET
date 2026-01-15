"""
Smart Copyright Expiry Tag Generator
Generates human-readable, auto-updating copyright status tags
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

from .rule_engine import get_rule_engine
from ..ml_model.predictor import get_predictor
from ..schemas import SmartTag, CopyrightStatus
from ..config import get_settings
from ..utils import format_years_duration

settings = get_settings()
logger = logging.getLogger(__name__)


class SmartTagGenerator:
    """
    Generates Smart Copyright Expiry Tags
    - Combines ML prediction with rule-based analysis
    - Produces human-readable output
    - Includes confidence scoring and AI reasoning
    """
    
    def __init__(self):
        self.rule_engine = get_rule_engine()
        self.predictor = get_predictor()
        self.tag_version = "1.0"
    
    def generate(
        self,
        title: str,
        creator: Optional[str] = None,
        publication_year: Optional[int] = None,
        creator_death_year: Optional[int] = None,
        content_type: Optional[str] = None,
        jurisdiction: str = "US",
        is_corporate_work: bool = False,
        is_anonymous: bool = False,
        source_urls: Optional[List[str]] = None,
        include_ai_reasoning: bool = True
    ) -> SmartTag:
        """
        Generate a complete Smart Copyright Expiry Tag
        """
        
        # Get ML prediction
        ml_prediction = self.predictor.predict(
            title=title,
            creator=creator,
            publication_year=publication_year,
            creator_death_year=creator_death_year,
            content_type=content_type,
            jurisdiction=jurisdiction
        )
        
        # Get rule-based analysis
        rule_analysis = self.rule_engine.analyze(
            title=title,
            creator=creator,
            publication_year=publication_year,
            creator_death_year=creator_death_year,
            content_type=content_type,
            jurisdiction=jurisdiction,
            is_corporate_work=is_corporate_work,
            is_anonymous=is_anonymous,
            ml_prediction=ml_prediction
        )
        
        # Determine status display
        status_display = self._get_status_display(rule_analysis['status'])
        
        # Generate timeline text
        expiry_timeline = self._generate_expiry_timeline(
            rule_analysis.get('years_until_expiry'),
            rule_analysis.get('is_expired', False),
            rule_analysis.get('expiry_date')
        )
        
        # Generate allowed uses summary
        allowed_summary = self._summarize_allowed_uses(rule_analysis.get('allowed_uses', []))
        
        # Calculate combined confidence
        confidence = self._calculate_combined_confidence(
            rule_confidence=rule_analysis['confidence'],
            ml_confidence=ml_prediction['confidence']
        )
        
        # Generate AI reasoning
        ai_reasoning = ""
        if include_ai_reasoning:
            ai_reasoning = self._generate_ai_reasoning(
                ml_prediction=ml_prediction,
                rule_analysis=rule_analysis,
                title=title,
                creator=creator
            )
        
        # Prepare data sources
        data_sources = source_urls or []
        if not data_sources:
            data_sources = ["Live web scraping", "AI analysis"]
        
        # Generate the tag
        return SmartTag(
            title=title,
            creator=creator,
            publication_year=publication_year,
            content_type=content_type,
            status_emoji=status_display['emoji'],
            status_text=status_display['text'],
            status_color=status_display['color'],
            expiry_date=rule_analysis.get('expiry_date').strftime('%Y-%m-%d') if rule_analysis.get('expiry_date') else None,
            expiry_timeline=expiry_timeline,
            allowed_uses_summary=allowed_summary,
            confidence_score=round(confidence, 2),
            confidence_level=self._confidence_to_level(confidence),
            ai_reasoning=ai_reasoning,
            data_sources=data_sources,
            generated_at=datetime.utcnow(),
            tag_version=self.tag_version,
            auto_update_enabled=True,
            next_verification_date=datetime.utcnow() + timedelta(days=30),
            disclaimer=self._generate_disclaimer(jurisdiction),
            jurisdiction=jurisdiction
        )
    
    def _get_status_display(self, status: CopyrightStatus) -> Dict[str, str]:
        """Get display properties for status"""
        
        status_map = {
            CopyrightStatus.PUBLIC_DOMAIN: {
                'emoji': '🌍',
                'text': 'Public Domain - Free to Use',
                'color': 'green'
            },
            CopyrightStatus.EXPIRED: {
                'emoji': '✅',
                'text': 'Copyright Expired - Free to Use',
                'color': 'green'
            },
            CopyrightStatus.LIKELY_EXPIRED: {
                'emoji': '🔁',
                'text': 'Likely Expired - Verify Before Commercial Use',
                'color': 'yellow'
            },
            CopyrightStatus.UNKNOWN: {
                'emoji': '❓',
                'text': 'Unknown Status - Research Required',
                'color': 'gray'
            },
            CopyrightStatus.LIKELY_ACTIVE: {
                'emoji': '⚠️',
                'text': 'Likely Protected - Permission May Be Required',
                'color': 'orange'
            },
            CopyrightStatus.ACTIVE: {
                'emoji': '❌',
                'text': 'All Rights Reserved - Permission Required',
                'color': 'red'
            },
        }
        
        return status_map.get(status, {
            'emoji': '❓',
            'text': 'Unknown',
            'color': 'gray'
        })
    
    def _generate_expiry_timeline(
        self,
        years_until_expiry: Optional[int],
        is_expired: bool,
        expiry_date: Optional[datetime]
    ) -> str:
        """Generate human-readable expiry timeline"""
        
        if is_expired:
            if years_until_expiry is not None:
                years_ago = abs(years_until_expiry)
                if years_ago == 0:
                    return "Expired this year"
                elif years_ago == 1:
                    return "Expired 1 year ago"
                else:
                    return f"Expired {years_ago} years ago"
            return "Expired (date unknown)"
        
        if years_until_expiry is not None:
            if years_until_expiry == 0:
                return "Expires this year"
            elif years_until_expiry == 1:
                return "Expires in 1 year"
            elif years_until_expiry <= 5:
                return f"Expires in {years_until_expiry} years (soon)"
            elif years_until_expiry <= 20:
                return f"Expires in {years_until_expiry} years"
            else:
                decade = (years_until_expiry // 10) * 10
                return f"Expires in ~{decade}+ years"
        
        if expiry_date:
            return f"Expires: {expiry_date.strftime('%B %d, %Y')}"
        
        return "Expiry date unknown"
    
    def _summarize_allowed_uses(self, allowed_uses: List[Dict[str, Any]]) -> List[str]:
        """Generate summary of allowed uses"""
        summary = []
        
        use_labels = {
            'personal': '👤 Personal Use',
            'educational': '📚 Educational Use',
            'commercial': '💼 Commercial Use',
            'remix': '🔄 Remix/Adaptation',
            'derivative': '🎨 Derivative Works',
            'distribution': '📤 Distribution'
        }
        
        for use in allowed_uses:
            use_type = use.get('use_type', '')
            is_allowed = use.get('is_allowed', False)
            conditions = use.get('conditions')
            
            label = use_labels.get(use_type, use_type.title())
            
            if is_allowed:
                if conditions:
                    summary.append(f"✓ {label} (with conditions)")
                else:
                    summary.append(f"✓ {label}")
            else:
                summary.append(f"✗ {label}")
        
        return summary
    
    def _calculate_combined_confidence(
        self,
        rule_confidence: float,
        ml_confidence: float
    ) -> float:
        """Calculate combined confidence score"""
        # Weighted average favoring rule-based when high
        if rule_confidence > 0.8:
            return 0.7 * rule_confidence + 0.3 * ml_confidence
        else:
            return 0.5 * rule_confidence + 0.5 * ml_confidence
    
    def _confidence_to_level(self, confidence: float) -> str:
        """Convert confidence score to level"""
        if confidence >= 0.8:
            return "High"
        elif confidence >= 0.6:
            return "Medium"
        elif confidence >= 0.4:
            return "Low"
        else:
            return "Very Low"
    
    def _generate_ai_reasoning(
        self,
        ml_prediction: Dict[str, Any],
        rule_analysis: Dict[str, Any],
        title: str,
        creator: Optional[str]
    ) -> str:
        """Generate comprehensive AI reasoning"""
        
        parts = []
        
        # Introduction
        if creator:
            parts.append(f"Analyzing \"{title}\" by {creator}.")
        else:
            parts.append(f"Analyzing \"{title}\".")
        
        # ML reasoning
        ml_reasoning = ml_prediction.get('reasoning', '')
        if ml_reasoning:
            parts.append(f"ML Analysis: {ml_reasoning}")
        
        # Rule-based reasoning
        rule_reasoning = rule_analysis.get('reasoning', '')
        if rule_reasoning:
            parts.append(f"Legal Analysis: {rule_reasoning}")
        
        # Uncertainties
        uncertainties = rule_analysis.get('uncertainties', [])
        if uncertainties:
            parts.append(f"Uncertainties: {', '.join(uncertainties)}.")
        
        # Feature importance from ML
        importance = ml_prediction.get('feature_importance', {})
        if importance:
            top_factors = list(importance.keys())[:3]
            if top_factors:
                formatted = [f.replace('_', ' ').title() for f in top_factors]
                parts.append(f"Key factors considered: {', '.join(formatted)}.")
        
        # Confidence explanation
        confidence = rule_analysis.get('confidence', 0.5)
        if confidence >= 0.8:
            parts.append("Analysis confidence is high based on available data.")
        elif confidence >= 0.6:
            parts.append("Analysis confidence is moderate; some data may be incomplete.")
        else:
            parts.append("Analysis confidence is low due to limited or uncertain data.")
        
        return " ".join(parts)
    
    def _generate_disclaimer(self, jurisdiction: str) -> str:
        """Generate legal disclaimer"""
        return (
            f"This analysis is based on {jurisdiction} copyright law and is provided for informational "
            f"purposes only. It does not constitute legal advice. Copyright status may vary by "
            f"jurisdiction and specific circumstances. Always consult a legal professional for "
            f"definitive guidance on copyright matters."
        )
    
    def generate_compact_tag(
        self,
        title: str,
        creator: Optional[str] = None,
        publication_year: Optional[int] = None,
        creator_death_year: Optional[int] = None,
        content_type: Optional[str] = None,
        jurisdiction: str = "US"
    ) -> str:
        """Generate a compact, single-line tag for embedding"""
        
        full_tag = self.generate(
            title=title,
            creator=creator,
            publication_year=publication_year,
            creator_death_year=creator_death_year,
            content_type=content_type,
            jurisdiction=jurisdiction,
            include_ai_reasoning=False
        )
        
        # Create compact format with better visuals
        confidence_bar = self._get_confidence_bar(full_tag.confidence_score)
        
        compact = (
            f"{full_tag.status_emoji} "
            f"[{full_tag.status_text}] "
            f"| ⏱ {full_tag.expiry_timeline} "
            f"| {confidence_bar} {full_tag.confidence_level} "
            f"| 🌐 {jurisdiction}"
        )
        
        return compact
    
    def _get_confidence_bar(self, score: float) -> str:
        """Generate visual confidence bar"""
        filled = int(score * 5)
        empty = 5 - filled
        return "█" * filled + "░" * empty
    
    def generate_detailed_tag(
        self,
        title: str,
        creator: Optional[str] = None,
        publication_year: Optional[int] = None,
        creator_death_year: Optional[int] = None,
        content_type: Optional[str] = None,
        jurisdiction: str = "US"
    ) -> Dict[str, Any]:
        """Generate a detailed tag with recommendations and actions"""
        
        tag = self.generate(
            title=title,
            creator=creator,
            publication_year=publication_year,
            creator_death_year=creator_death_year,
            content_type=content_type,
            jurisdiction=jurisdiction
        )
        
        # Generate recommendations based on status
        recommendations = self._generate_recommendations(tag)
        
        # Generate quick actions
        quick_actions = self._generate_quick_actions(tag)
        
        # Generate risk assessment
        risk_assessment = self._generate_risk_assessment(tag)
        
        return {
            "tag": tag,
            "recommendations": recommendations,
            "quick_actions": quick_actions,
            "risk_assessment": risk_assessment,
            "summary": self._generate_summary(tag),
            "legal_checklist": self._generate_legal_checklist(tag)
        }
    
    def _generate_recommendations(self, tag: SmartTag) -> List[Dict[str, str]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if tag.status_text.startswith("Public Domain"):
            recommendations.append({
                "icon": "✅",
                "type": "success",
                "title": "Free to Use",
                "description": "This work is in the public domain. You can use, modify, and distribute it freely without permission."
            })
            recommendations.append({
                "icon": "💡",
                "type": "tip",
                "title": "Attribution Optional",
                "description": "While not legally required, crediting the original creator is good practice."
            })
        elif "Expired" in tag.status_text:
            recommendations.append({
                "icon": "✅",
                "type": "success",
                "title": "Copyright Expired",
                "description": "The copyright has expired. This work can now be used freely."
            })
            recommendations.append({
                "icon": "⚠️",
                "type": "warning",
                "title": "Verify Editions",
                "description": "Note that newer editions or translations may still be under copyright."
            })
        elif "Likely Expired" in tag.status_text:
            recommendations.append({
                "icon": "🔍",
                "type": "info",
                "title": "Verification Recommended",
                "description": "The copyright has likely expired, but we recommend verification before commercial use."
            })
            recommendations.append({
                "icon": "📞",
                "type": "action",
                "title": "Contact Copyright Office",
                "description": f"Check with the {tag.jurisdiction} copyright office for official records."
            })
        elif "Protected" in tag.status_text or "Reserved" in tag.status_text:
            recommendations.append({
                "icon": "🔒",
                "type": "warning",
                "title": "Permission Required",
                "description": "This work is protected. You need permission from the copyright holder for most uses."
            })
            recommendations.append({
                "icon": "📝",
                "type": "action",
                "title": "Fair Use Exceptions",
                "description": "Limited use may be allowed for criticism, education, or parody under fair use/fair dealing."
            })
            recommendations.append({
                "icon": "💰",
                "type": "info",
                "title": "Licensing Options",
                "description": "Consider purchasing a license or contacting the rights holder for permission."
            })
        else:
            recommendations.append({
                "icon": "🔍",
                "type": "warning",
                "title": "Research Required",
                "description": "Copyright status is unclear. Additional research is recommended before use."
            })
        
        return recommendations
    
    def _generate_quick_actions(self, tag: SmartTag) -> List[Dict[str, str]]:
        """Generate quick action buttons/links"""
        actions = []
        
        if tag.status_color in ['green']:
            actions.append({"label": "📥 Download Tag", "action": "download"})
            actions.append({"label": "📤 Share", "action": "share"})
            actions.append({"label": "📋 Copy Citation", "action": "copy_citation"})
        else:
            actions.append({"label": "📧 Request Permission", "action": "request_permission"})
            actions.append({"label": "🔍 Find Alternatives", "action": "find_alternatives"})
            actions.append({"label": "📚 Check Fair Use", "action": "fair_use_guide"})
        
        actions.append({"label": "📊 Full Report", "action": "full_report"})
        
        return actions
    
    def _generate_risk_assessment(self, tag: SmartTag) -> Dict[str, Any]:
        """Generate risk assessment for using the work"""
        
        if tag.status_color == 'green':
            return {
                "level": "Low",
                "color": "#28a745",
                "icon": "✅",
                "score": 1,
                "description": "Minimal legal risk. Safe for all uses.",
                "commercial_risk": "Low",
                "personal_risk": "None"
            }
        elif tag.status_color == 'yellow':
            return {
                "level": "Medium",
                "color": "#ffc107",
                "icon": "⚠️",
                "score": 3,
                "description": "Moderate risk. Verification recommended.",
                "commercial_risk": "Medium",
                "personal_risk": "Low"
            }
        elif tag.status_color == 'orange':
            return {
                "level": "High",
                "color": "#fd7e14",
                "icon": "🔶",
                "score": 4,
                "description": "High risk without permission. Fair use may apply.",
                "commercial_risk": "High",
                "personal_risk": "Medium"
            }
        elif tag.status_color == 'red':
            return {
                "level": "Very High",
                "color": "#dc3545",
                "icon": "🔴",
                "score": 5,
                "description": "Very high risk. Permission required for most uses.",
                "commercial_risk": "Very High",
                "personal_risk": "Medium"
            }
        else:
            return {
                "level": "Unknown",
                "color": "#6c757d",
                "icon": "❓",
                "score": 3,
                "description": "Risk unclear. Research recommended.",
                "commercial_risk": "Unknown",
                "personal_risk": "Unknown"
            }
    
    def _generate_summary(self, tag: SmartTag) -> str:
        """Generate a one-paragraph summary"""
        
        creator_text = f" by {tag.creator}" if tag.creator else ""
        year_text = f" ({tag.publication_year})" if tag.publication_year else ""
        
        if tag.status_color == 'green':
            return (
                f'"{tag.title}"{creator_text}{year_text} is in the public domain. '
                f"You are free to use, copy, modify, and distribute this work without restriction. "
                f"Our analysis has {tag.confidence_level.lower()} confidence ({tag.confidence_score:.0%})."
            )
        elif tag.status_color in ['yellow', 'orange']:
            return (
                f'"{tag.title}"{creator_text}{year_text} may still be under copyright protection. '
                f"{tag.expiry_timeline}. We recommend verifying the status before commercial use. "
                f"Analysis confidence: {tag.confidence_level} ({tag.confidence_score:.0%})."
            )
        elif tag.status_color == 'red':
            return (
                f'"{tag.title}"{creator_text}{year_text} is under active copyright protection. '
                f"{tag.expiry_timeline}. You need permission from the copyright holder for most uses. "
                f"Limited exceptions may apply under fair use/fair dealing."
            )
        else:
            return (
                f'The copyright status of "{tag.title}"{creator_text}{year_text} could not be determined with certainty. '
                f"We recommend additional research before using this work."
            )
    
    def _generate_legal_checklist(self, tag: SmartTag) -> List[Dict[str, Any]]:
        """Generate a legal checklist for the user"""
        checklist = []
        
        if tag.status_color == 'green':
            checklist = [
                {"item": "Verify this is the original work, not a new edition", "required": False, "status": "recommended"},
                {"item": "Credit the original creator (optional but recommended)", "required": False, "status": "optional"},
                {"item": "Check for trademark issues if using title/brand", "required": True, "status": "recommended"}
            ]
        else:
            checklist = [
                {"item": "Identify the copyright holder", "required": True, "status": "required"},
                {"item": "Determine if fair use applies to your use case", "required": True, "status": "required"},
                {"item": "Obtain written permission if needed", "required": True, "status": "required"},
                {"item": "Keep records of all permissions", "required": True, "status": "required"},
                {"item": "Check if a license is available for purchase", "required": False, "status": "optional"}
            ]
        
        return checklist
    
    def generate_html_tag(
        self,
        title: str,
        creator: Optional[str] = None,
        publication_year: Optional[int] = None,
        creator_death_year: Optional[int] = None,
        content_type: Optional[str] = None,
        jurisdiction: str = "US"
    ) -> str:
        """Generate an HTML-formatted tag for web embedding"""
        
        tag = self.generate(
            title=title,
            creator=creator,
            publication_year=publication_year,
            creator_death_year=creator_death_year,
            content_type=content_type,
            jurisdiction=jurisdiction
        )
        
        color_map = {
            'green': '#28a745',
            'yellow': '#ffc107',
            'orange': '#fd7e14',
            'red': '#dc3545',
            'gray': '#6c757d'
        }
        
        bg_color = color_map.get(tag.status_color, '#6c757d')
        
        html = f'''
<div class="scet-tag" style="border: 2px solid {bg_color}; border-radius: 8px; padding: 16px; max-width: 400px; font-family: Arial, sans-serif;">
    <div style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="font-size: 24px; margin-right: 8px;">{tag.status_emoji}</span>
        <span style="font-weight: bold; color: {bg_color};">{tag.status_text}</span>
    </div>
    <div style="margin-bottom: 8px;">
        <strong>{tag.title}</strong>
        {f'<br><em>by {tag.creator}</em>' if tag.creator else ''}
        {f'<br>Published: {tag.publication_year}' if tag.publication_year else ''}
    </div>
    <div style="background: #f8f9fa; padding: 8px; border-radius: 4px; margin-bottom: 8px;">
        ⏱ {tag.expiry_timeline}
    </div>
    <div style="font-size: 12px; color: #666;">
        Confidence: {tag.confidence_level} ({tag.confidence_score:.0%}) | {tag.jurisdiction}
        <br>Generated: {tag.generated_at.strftime('%Y-%m-%d')} | SCET v{tag.tag_version}
    </div>
</div>
'''
        return html


# Singleton instance
_generator: Optional[SmartTagGenerator] = None


def get_tag_generator() -> SmartTagGenerator:
    """Get or create tag generator instance"""
    global _generator
    if _generator is None:
        _generator = SmartTagGenerator()
    return _generator
