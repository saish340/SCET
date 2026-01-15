"""
Copyright Rule Engine
Applies legal copyright rules based on jurisdiction, year, creator status, etc.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import logging

from ..config import get_settings
from ..schemas import CopyrightStatus, AllowedUse

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class JurisdictionRules:
    """Copyright rules for a specific jurisdiction"""
    code: str
    name: str
    standard_duration: int  # Years after author death
    corporate_duration: int  # Years from publication for corporate works
    anonymous_duration: int  # Years for anonymous works
    public_domain_before: Optional[int]  # Works published before this year are PD
    requires_registration: bool
    notes: str


# Jurisdiction rules database (built-in, not from external dataset)
JURISDICTION_RULES = {
    "US": JurisdictionRules(
        code="US",
        name="United States",
        standard_duration=70,
        corporate_duration=95,
        anonymous_duration=95,
        public_domain_before=1929,  # As of 2024, works before 1929 are PD
        requires_registration=False,  # Not since 1989
        notes="Copyright term varies based on publication date and registration status"
    ),
    "EU": JurisdictionRules(
        code="EU",
        name="European Union",
        standard_duration=70,
        corporate_duration=70,
        anonymous_duration=70,
        public_domain_before=None,  # Depends on author death
        requires_registration=False,
        notes="Harmonized across EU member states"
    ),
    "UK": JurisdictionRules(
        code="UK",
        name="United Kingdom",
        standard_duration=70,
        corporate_duration=70,
        anonymous_duration=70,
        public_domain_before=None,
        requires_registration=False,
        notes="Similar to EU rules, post-Brexit maintains same durations"
    ),
    "CA": JurisdictionRules(
        code="CA",
        name="Canada",
        standard_duration=70,  # Changed from 50 to 70 in 2022
        corporate_duration=75,
        anonymous_duration=75,
        public_domain_before=None,
        requires_registration=False,
        notes="Extended to 70 years as of December 2022"
    ),
    "AU": JurisdictionRules(
        code="AU",
        name="Australia",
        standard_duration=70,
        corporate_duration=70,
        anonymous_duration=70,
        public_domain_before=None,
        requires_registration=False,
        notes="70 years since 2005"
    ),
    "JP": JurisdictionRules(
        code="JP",
        name="Japan",
        standard_duration=70,
        corporate_duration=70,
        anonymous_duration=70,
        public_domain_before=None,
        requires_registration=False,
        notes="Extended to 70 years in 2018"
    ),
    "IN": JurisdictionRules(
        code="IN",
        name="India",
        standard_duration=60,
        corporate_duration=60,
        anonymous_duration=60,
        public_domain_before=None,
        requires_registration=False,
        notes="60 years after author death"
    ),
}


# ============ Software License Rules ============

SOFTWARE_LICENSES = {
    "MIT": {
        "name": "MIT License",
        "type": "permissive",
        "commercial_use": True,
        "modification": True,
        "distribution": True,
        "private_use": True,
        "patent_rights": False,
        "conditions": ["Include copyright notice", "Include license text"],
        "limitations": ["No liability", "No warranty"],
    },
    "GPL-3.0": {
        "name": "GNU General Public License v3.0",
        "type": "copyleft",
        "commercial_use": True,
        "modification": True,
        "distribution": True,
        "private_use": True,
        "patent_rights": True,
        "conditions": ["Disclose source", "Same license", "Include copyright", "State changes"],
        "limitations": ["No liability", "No warranty"],
    },
    "GPL-2.0": {
        "name": "GNU General Public License v2.0",
        "type": "copyleft",
        "commercial_use": True,
        "modification": True,
        "distribution": True,
        "private_use": True,
        "patent_rights": False,
        "conditions": ["Disclose source", "Same license", "Include copyright", "State changes"],
        "limitations": ["No liability", "No warranty"],
    },
    "Apache-2.0": {
        "name": "Apache License 2.0",
        "type": "permissive",
        "commercial_use": True,
        "modification": True,
        "distribution": True,
        "private_use": True,
        "patent_rights": True,
        "conditions": ["Include copyright", "Include license", "State changes", "Include NOTICE"],
        "limitations": ["No trademark rights", "No liability", "No warranty"],
    },
    "BSD-3-Clause": {
        "name": "BSD 3-Clause License",
        "type": "permissive",
        "commercial_use": True,
        "modification": True,
        "distribution": True,
        "private_use": True,
        "patent_rights": False,
        "conditions": ["Include copyright notice", "No endorsement clause"],
        "limitations": ["No liability", "No warranty"],
    },
    "BSD-2-Clause": {
        "name": "BSD 2-Clause License",
        "type": "permissive",
        "commercial_use": True,
        "modification": True,
        "distribution": True,
        "private_use": True,
        "patent_rights": False,
        "conditions": ["Include copyright notice"],
        "limitations": ["No liability", "No warranty"],
    },
    "LGPL": {
        "name": "GNU Lesser General Public License",
        "type": "weak_copyleft",
        "commercial_use": True,
        "modification": True,
        "distribution": True,
        "private_use": True,
        "patent_rights": False,
        "conditions": ["Disclose source of library", "Same license for library"],
        "limitations": ["No liability", "No warranty"],
    },
    "MPL-2.0": {
        "name": "Mozilla Public License 2.0",
        "type": "weak_copyleft",
        "commercial_use": True,
        "modification": True,
        "distribution": True,
        "private_use": True,
        "patent_rights": True,
        "conditions": ["Disclose source of modified files", "Same license for modified files"],
        "limitations": ["No trademark rights", "No liability", "No warranty"],
    },
    "Unlicense": {
        "name": "The Unlicense",
        "type": "public_domain",
        "commercial_use": True,
        "modification": True,
        "distribution": True,
        "private_use": True,
        "patent_rights": False,
        "conditions": [],
        "limitations": ["No liability", "No warranty"],
    },
    "CC0-1.0": {
        "name": "Creative Commons Zero v1.0",
        "type": "public_domain",
        "commercial_use": True,
        "modification": True,
        "distribution": True,
        "private_use": True,
        "patent_rights": False,
        "conditions": [],
        "limitations": ["No liability", "No warranty", "No trademark rights", "No patent rights"],
    },
    "Proprietary": {
        "name": "Proprietary License",
        "type": "proprietary",
        "commercial_use": False,
        "modification": False,
        "distribution": False,
        "private_use": True,
        "patent_rights": False,
        "conditions": ["Varies by license agreement"],
        "limitations": ["All rights reserved"],
    },
}


# ============ Patent Rules ============

PATENT_RULES = {
    "US": {
        "duration": 20,  # Years from filing date
        "type": "utility",
        "renewable": False,
        "notes": "Design patents: 15 years, Plant patents: 20 years",
    },
    "EU": {
        "duration": 20,
        "type": "utility",
        "renewable": False,
        "notes": "European Patent Convention, annual maintenance fees required",
    },
    "CN": {
        "duration": 20,
        "type": "utility",
        "renewable": False,
        "notes": "Design patents: 15 years, Utility models: 10 years",
    },
}


# ============ Trademark Rules ============

TRADEMARK_RULES = {
    "US": {
        "initial_duration": 10,  # Years
        "renewal_period": 10,
        "indefinite_renewal": True,
        "use_requirement": True,
        "notes": "Must file Declaration of Use between 5th and 6th year",
    },
    "EU": {
        "initial_duration": 10,
        "renewal_period": 10,
        "indefinite_renewal": True,
        "use_requirement": True,
        "notes": "EU-wide protection through EUIPO",
    },
}


class CopyrightRuleEngine:
    """
    Rule engine for determining copyright status
    Combines legal rules with ML predictions for comprehensive analysis
    """
    
    def __init__(self):
        self.current_year = datetime.now().year
        self.jurisdictions = JURISDICTION_RULES
    
    def analyze(
        self,
        title: str,
        creator: Optional[str] = None,
        publication_year: Optional[int] = None,
        creator_death_year: Optional[int] = None,
        content_type: Optional[str] = None,
        jurisdiction: str = "US",
        is_corporate_work: bool = False,
        is_anonymous: bool = False,
        ml_prediction: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze copyright status using legal rules
        """
        rules = self.jurisdictions.get(jurisdiction, self.jurisdictions["US"])
        
        # Determine copyright status
        status, confidence, reasoning = self._determine_status(
            publication_year=publication_year,
            creator_death_year=creator_death_year,
            is_corporate_work=is_corporate_work,
            is_anonymous=is_anonymous,
            rules=rules
        )
        
        # Calculate expiry
        expiry_info = self._calculate_expiry(
            publication_year=publication_year,
            creator_death_year=creator_death_year,
            is_corporate_work=is_corporate_work,
            is_anonymous=is_anonymous,
            rules=rules
        )
        
        # Determine allowed uses
        allowed_uses = self._determine_allowed_uses(status, content_type)
        
        # Combine with ML prediction if available
        if ml_prediction:
            combined_status, combined_confidence = self._combine_with_ml(
                rule_status=status,
                rule_confidence=confidence,
                ml_prediction=ml_prediction
            )
            status = combined_status
            confidence = combined_confidence
        
        # Generate uncertainties
        uncertainties = self._identify_uncertainties(
            publication_year, creator_death_year, is_corporate_work, creator
        )
        
        return {
            'status': status,
            'confidence': confidence,
            'expiry_date': expiry_info.get('expiry_date'),
            'years_until_expiry': expiry_info.get('years_until_expiry'),
            'is_expired': expiry_info.get('is_expired', False),
            'allowed_uses': allowed_uses,
            'reasoning': reasoning,
            'uncertainties': uncertainties,
            'jurisdiction': jurisdiction,
            'jurisdiction_name': rules.name,
            'rules_applied': self._get_rules_applied(rules, is_corporate_work, is_anonymous)
        }
    
    def _determine_status(
        self,
        publication_year: Optional[int],
        creator_death_year: Optional[int],
        is_corporate_work: bool,
        is_anonymous: bool,
        rules: JurisdictionRules
    ) -> Tuple[CopyrightStatus, float, str]:
        """Determine copyright status based on rules"""
        
        reasoning_parts = []
        
        # Check public domain threshold
        if publication_year and rules.public_domain_before:
            if publication_year < rules.public_domain_before:
                reasoning_parts.append(
                    f"Work published in {publication_year}, before {rules.public_domain_before} "
                    f"(public domain threshold for {rules.code})"
                )
                return CopyrightStatus.PUBLIC_DOMAIN, 0.95, "; ".join(reasoning_parts)
        
        # Check based on creator death + duration
        if creator_death_year and not is_corporate_work:
            years_since_death = self.current_year - creator_death_year
            
            if years_since_death >= rules.standard_duration:
                reasoning_parts.append(
                    f"Creator died in {creator_death_year}, {years_since_death} years ago. "
                    f"Copyright expired after {rules.standard_duration} years."
                )
                return CopyrightStatus.EXPIRED, 0.9, "; ".join(reasoning_parts)
            elif years_since_death >= rules.standard_duration - 5:
                reasoning_parts.append(
                    f"Creator died in {creator_death_year}. "
                    f"Copyright likely expiring within 5 years."
                )
                return CopyrightStatus.LIKELY_EXPIRED, 0.7, "; ".join(reasoning_parts)
            else:
                years_remaining = rules.standard_duration - years_since_death
                reasoning_parts.append(
                    f"Creator died in {creator_death_year}. "
                    f"Copyright protected for approximately {years_remaining} more years."
                )
                return CopyrightStatus.ACTIVE, 0.85, "; ".join(reasoning_parts)
        
        # Check corporate/anonymous works based on publication year
        if is_corporate_work or is_anonymous:
            duration = rules.corporate_duration if is_corporate_work else rules.anonymous_duration
            
            if publication_year:
                years_since_pub = self.current_year - publication_year
                
                if years_since_pub >= duration:
                    work_type = "Corporate" if is_corporate_work else "Anonymous"
                    reasoning_parts.append(
                        f"{work_type} work published in {publication_year}. "
                        f"Copyright expired after {duration} years."
                    )
                    return CopyrightStatus.EXPIRED, 0.85, "; ".join(reasoning_parts)
                else:
                    years_remaining = duration - years_since_pub
                    reasoning_parts.append(
                        f"Work published in {publication_year}. "
                        f"Protected for approximately {years_remaining} more years."
                    )
                    return CopyrightStatus.ACTIVE, 0.8, "; ".join(reasoning_parts)
        
        # If we have publication year but no death year
        if publication_year:
            years_since_pub = self.current_year - publication_year
            
            # Very old works are likely public domain
            if years_since_pub > 150:
                reasoning_parts.append(
                    f"Work published {years_since_pub} years ago. "
                    f"Highly likely to be in public domain."
                )
                return CopyrightStatus.PUBLIC_DOMAIN, 0.8, "; ".join(reasoning_parts)
            elif years_since_pub > 100:
                reasoning_parts.append(
                    f"Work published {years_since_pub} years ago. "
                    f"Likely in public domain, but creator death year unknown."
                )
                return CopyrightStatus.LIKELY_EXPIRED, 0.65, "; ".join(reasoning_parts)
            elif years_since_pub > 70:
                reasoning_parts.append(
                    f"Work published {years_since_pub} years ago. "
                    f"Status uncertain without creator death information."
                )
                return CopyrightStatus.UNKNOWN, 0.5, "; ".join(reasoning_parts)
            elif years_since_pub < 50:
                reasoning_parts.append(
                    f"Work published in {publication_year}. "
                    f"Likely still under copyright protection."
                )
                return CopyrightStatus.LIKELY_ACTIVE, 0.7, "; ".join(reasoning_parts)
        
        # Unknown - insufficient data
        reasoning_parts.append(
            "Insufficient data to determine copyright status. "
            "Publication year and/or creator death year unknown."
        )
        return CopyrightStatus.UNKNOWN, 0.3, "; ".join(reasoning_parts)
    
    def _calculate_expiry(
        self,
        publication_year: Optional[int],
        creator_death_year: Optional[int],
        is_corporate_work: bool,
        is_anonymous: bool,
        rules: JurisdictionRules
    ) -> Dict[str, Any]:
        """Calculate copyright expiry date"""
        
        # Already in public domain (pre-threshold)
        if publication_year and rules.public_domain_before:
            if publication_year < rules.public_domain_before:
                return {
                    'expiry_date': None,
                    'years_until_expiry': 0,
                    'is_expired': True,
                    'expiry_basis': 'public_domain_threshold'
                }
        
        # Calculate based on death year
        if creator_death_year and not is_corporate_work and not is_anonymous:
            expiry_year = creator_death_year + rules.standard_duration
            years_until = expiry_year - self.current_year
            
            return {
                'expiry_date': datetime(expiry_year, 12, 31) if years_until > 0 else None,
                'years_until_expiry': max(0, years_until),
                'is_expired': years_until <= 0,
                'expiry_basis': f'creator_death + {rules.standard_duration} years'
            }
        
        # Calculate based on publication year (corporate/anonymous)
        if publication_year and (is_corporate_work or is_anonymous):
            duration = rules.corporate_duration if is_corporate_work else rules.anonymous_duration
            expiry_year = publication_year + duration
            years_until = expiry_year - self.current_year
            
            return {
                'expiry_date': datetime(expiry_year, 12, 31) if years_until > 0 else None,
                'years_until_expiry': max(0, years_until),
                'is_expired': years_until <= 0,
                'expiry_basis': f'publication + {duration} years'
            }
        
        # Estimate if we only have publication year
        if publication_year:
            # Assume author was 30 at publication and lived to 75
            estimated_death = publication_year + 45
            expiry_year = estimated_death + rules.standard_duration
            years_until = expiry_year - self.current_year
            
            return {
                'expiry_date': datetime(expiry_year, 12, 31) if years_until > 0 else None,
                'years_until_expiry': max(0, years_until) if years_until > 0 else None,
                'is_expired': years_until <= 0,
                'expiry_basis': 'estimated (publication year only)'
            }
        
        return {
            'expiry_date': None,
            'years_until_expiry': None,
            'is_expired': False,
            'expiry_basis': 'unknown'
        }
    
    def _determine_allowed_uses(
        self,
        status: CopyrightStatus,
        content_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Determine allowed uses based on copyright status"""
        
        all_uses = [
            AllowedUse.PERSONAL,
            AllowedUse.EDUCATIONAL,
            AllowedUse.COMMERCIAL,
            AllowedUse.REMIX,
            AllowedUse.DERIVATIVE,
            AllowedUse.DISTRIBUTION
        ]
        
        allowed_uses = []
        
        for use in all_uses:
            is_allowed, conditions, confidence = self._check_use_allowed(
                use, status, content_type
            )
            
            allowed_uses.append({
                'use_type': use.value,
                'is_allowed': is_allowed,
                'conditions': conditions,
                'confidence': confidence
            })
        
        return allowed_uses
    
    def _check_use_allowed(
        self,
        use: AllowedUse,
        status: CopyrightStatus,
        content_type: Optional[str]
    ) -> Tuple[bool, Optional[str], float]:
        """Check if a specific use is allowed"""
        
        if status == CopyrightStatus.PUBLIC_DOMAIN:
            return True, None, 0.95
        
        if status == CopyrightStatus.EXPIRED:
            return True, None, 0.9
        
        if status == CopyrightStatus.LIKELY_EXPIRED:
            return True, "Verify expiry before commercial use", 0.7
        
        if status == CopyrightStatus.ACTIVE:
            if use == AllowedUse.PERSONAL:
                return True, "Personal use typically permitted", 0.8
            elif use == AllowedUse.EDUCATIONAL:
                return True, "Fair use for educational purposes may apply", 0.6
            else:
                return False, "Requires permission from rights holder", 0.8
        
        if status == CopyrightStatus.LIKELY_ACTIVE:
            if use in [AllowedUse.PERSONAL, AllowedUse.EDUCATIONAL]:
                return True, "Likely permitted under fair use", 0.6
            else:
                return False, "Likely requires permission", 0.7
        
        # Unknown status
        return False, "Copyright status unclear; obtain permission to be safe", 0.4
    
    def _combine_with_ml(
        self,
        rule_status: CopyrightStatus,
        rule_confidence: float,
        ml_prediction: Dict[str, Any]
    ) -> Tuple[CopyrightStatus, float]:
        """Combine rule-based analysis with ML prediction"""
        
        ml_probability = ml_prediction.get('probability_public_domain', 0.5)
        ml_confidence = ml_prediction.get('confidence', 0.5)
        
        # Weight: 60% rules, 40% ML
        rule_weight = 0.6
        ml_weight = 0.4
        
        # Convert rule status to probability
        status_to_prob = {
            CopyrightStatus.PUBLIC_DOMAIN: 0.95,
            CopyrightStatus.EXPIRED: 0.9,
            CopyrightStatus.LIKELY_EXPIRED: 0.7,
            CopyrightStatus.UNKNOWN: 0.5,
            CopyrightStatus.LIKELY_ACTIVE: 0.3,
            CopyrightStatus.ACTIVE: 0.1,
        }
        
        rule_prob = status_to_prob.get(rule_status, 0.5)
        
        # Weighted combination
        combined_prob = (rule_prob * rule_weight + ml_probability * ml_weight)
        combined_confidence = (rule_confidence * rule_weight + ml_confidence * ml_weight)
        
        # Determine final status
        if combined_prob >= 0.85:
            final_status = CopyrightStatus.PUBLIC_DOMAIN
        elif combined_prob >= 0.65:
            final_status = CopyrightStatus.LIKELY_EXPIRED
        elif combined_prob >= 0.35:
            final_status = CopyrightStatus.UNKNOWN
        elif combined_prob >= 0.15:
            final_status = CopyrightStatus.LIKELY_ACTIVE
        else:
            final_status = CopyrightStatus.ACTIVE
        
        return final_status, combined_confidence
    
    def _identify_uncertainties(
        self,
        publication_year: Optional[int],
        creator_death_year: Optional[int],
        is_corporate_work: bool,
        creator: Optional[str]
    ) -> List[str]:
        """Identify factors that create uncertainty"""
        uncertainties = []
        
        if not publication_year:
            uncertainties.append("Publication year unknown")
        
        if not creator_death_year and not is_corporate_work:
            uncertainties.append("Creator death year unknown")
        
        if not creator:
            uncertainties.append("Creator/author unknown")
        
        if is_corporate_work:
            uncertainties.append("Corporate authorship may have special rules")
        
        return uncertainties
    
    def _get_rules_applied(
        self,
        rules: JurisdictionRules,
        is_corporate_work: bool,
        is_anonymous: bool
    ) -> List[str]:
        """Get list of rules that were applied"""
        applied = []
        
        applied.append(f"Jurisdiction: {rules.name} ({rules.code})")
        
        if is_corporate_work:
            applied.append(f"Corporate work rule: {rules.corporate_duration} years from publication")
        elif is_anonymous:
            applied.append(f"Anonymous work rule: {rules.anonymous_duration} years from publication")
        else:
            applied.append(f"Standard rule: {rules.standard_duration} years after creator death")
        
        if rules.public_domain_before:
            applied.append(f"Works published before {rules.public_domain_before} are public domain")
        
        return applied
    
    def get_jurisdiction_info(self, code: str) -> Optional[Dict[str, Any]]:
        """Get information about a jurisdiction"""
        rules = self.jurisdictions.get(code.upper())
        if not rules:
            return None
        
        return {
            'code': rules.code,
            'name': rules.name,
            'standard_duration': rules.standard_duration,
            'corporate_duration': rules.corporate_duration,
            'anonymous_duration': rules.anonymous_duration,
            'public_domain_before': rules.public_domain_before,
            'requires_registration': rules.requires_registration,
            'notes': rules.notes
        }
    
    def list_jurisdictions(self) -> List[Dict[str, str]]:
        """List all supported jurisdictions"""
        return [
            {'code': rules.code, 'name': rules.name}
            for rules in self.jurisdictions.values()
        ]
    
    # ============ Software/Code Analysis ============
    
    def analyze_software(
        self,
        title: str,
        license_id: Optional[str] = None,
        creator: Optional[str] = None,
        publication_year: Optional[int] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze software license and permissions"""
        
        additional_data = additional_data or {}
        license_id = license_id or additional_data.get('license', 'Unknown')
        
        # Normalize license ID
        license_id = license_id.upper().replace(' ', '-') if license_id else 'Unknown'
        
        # Try to find matching license
        license_info = None
        for key, info in SOFTWARE_LICENSES.items():
            if key.upper() in license_id or license_id in key.upper():
                license_info = info
                license_id = key
                break
        
        if not license_info:
            license_info = SOFTWARE_LICENSES.get('Proprietary')
            license_id = 'Unknown'
        
        # Determine status
        if license_info['type'] == 'public_domain':
            status = 'public_domain'
            status_text = 'Public Domain / Fully Open'
            emoji = '🌍'
        elif license_info['type'] in ['permissive', 'weak_copyleft']:
            status = 'open_source'
            status_text = f"Open Source ({license_info['type'].replace('_', ' ').title()})"
            emoji = '✅'
        elif license_info['type'] == 'copyleft':
            status = 'copyleft'
            status_text = 'Open Source (Copyleft - Share-alike required)'
            emoji = '🔄'
        else:
            status = 'proprietary'
            status_text = 'Proprietary - Restricted Use'
            emoji = '🔒'
        
        # Build allowed uses
        allowed_uses = []
        if license_info.get('private_use'):
            allowed_uses.append({'use': 'personal', 'allowed': True, 'conditions': None})
        if license_info.get('commercial_use'):
            allowed_uses.append({'use': 'commercial', 'allowed': True, 'conditions': license_info.get('conditions')})
        else:
            allowed_uses.append({'use': 'commercial', 'allowed': False, 'conditions': ['License prohibits commercial use']})
        if license_info.get('modification'):
            allowed_uses.append({'use': 'modification', 'allowed': True, 'conditions': license_info.get('conditions')})
        if license_info.get('distribution'):
            allowed_uses.append({'use': 'distribution', 'allowed': True, 'conditions': license_info.get('conditions')})
        
        return {
            'content_type': 'software',
            'license_id': license_id,
            'license_name': license_info['name'],
            'license_type': license_info['type'],
            'status': status,
            'status_text': status_text,
            'status_emoji': emoji,
            'allowed_uses': allowed_uses,
            'conditions': license_info.get('conditions', []),
            'limitations': license_info.get('limitations', []),
            'patent_rights': license_info.get('patent_rights', False),
            'confidence': 0.95 if license_id != 'Unknown' else 0.5,
            'reasoning': f"Software licensed under {license_info['name']}. {license_info['type'].replace('_', ' ').title()} license.",
            'expires': False,  # Software licenses don't expire
            'note': 'Software licenses are perpetual unless violated'
        }
    
    # ============ Patent Analysis ============
    
    def analyze_patent(
        self,
        title: str,
        publication_year: Optional[int] = None,
        jurisdiction: str = "US",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze patent status"""
        
        additional_data = additional_data or {}
        patent_rules = PATENT_RULES.get(jurisdiction, PATENT_RULES['US'])
        
        # Calculate patent status
        duration = patent_rules['duration']
        filing_year = publication_year or additional_data.get('filing_year')
        
        if filing_year:
            years_since_filing = self.current_year - filing_year
            years_remaining = duration - years_since_filing
            
            if years_remaining <= 0:
                status = 'expired'
                status_text = 'Patent Expired - Free to Use'
                emoji = '🌍'
            else:
                status = 'active'
                status_text = f'Patent Active - {years_remaining} years remaining'
                emoji = '⚠️'
        else:
            status = 'unknown'
            status_text = 'Patent Status Unknown'
            emoji = '❓'
            years_remaining = None
        
        # Allowed uses for patents
        if status == 'expired':
            allowed_uses = [
                {'use': 'personal', 'allowed': True, 'conditions': None},
                {'use': 'commercial', 'allowed': True, 'conditions': None},
                {'use': 'manufacturing', 'allowed': True, 'conditions': None},
            ]
        else:
            allowed_uses = [
                {'use': 'personal', 'allowed': False, 'conditions': ['Requires license from patent holder']},
                {'use': 'commercial', 'allowed': False, 'conditions': ['Requires license from patent holder']},
                {'use': 'research', 'allowed': True, 'conditions': ['Research exemption may apply']},
            ]
        
        return {
            'content_type': 'patent',
            'ip_type': 'patent',
            'status': status,
            'status_text': status_text,
            'status_emoji': emoji,
            'duration_years': duration,
            'filing_year': filing_year,
            'expiry_year': filing_year + duration if filing_year else None,
            'years_remaining': max(0, years_remaining) if years_remaining else None,
            'allowed_uses': allowed_uses,
            'jurisdiction': jurisdiction,
            'confidence': 0.85 if filing_year else 0.5,
            'reasoning': f"Patent filed in {filing_year}. Standard {duration}-year protection period in {jurisdiction}." if filing_year else "Filing year unknown.",
            'note': patent_rules.get('notes', ''),
        }
    
    # ============ Trademark Analysis ============
    
    def analyze_trademark(
        self,
        title: str,
        registration_year: Optional[int] = None,
        jurisdiction: str = "US",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze trademark status"""
        
        additional_data = additional_data or {}
        tm_rules = TRADEMARK_RULES.get(jurisdiction, TRADEMARK_RULES['US'])
        
        # Trademarks can be renewed indefinitely
        if additional_data.get('ip_status') == 'abandoned':
            status = 'abandoned'
            status_text = 'Trademark Abandoned'
            emoji = '🌍'
        elif additional_data.get('ip_status') == 'cancelled':
            status = 'cancelled'
            status_text = 'Trademark Cancelled'
            emoji = '🌍'
        else:
            status = 'active'
            status_text = 'Trademark Active (Renewable Indefinitely)'
            emoji = '®️'
        
        # Allowed uses for trademarks
        if status in ['abandoned', 'cancelled']:
            allowed_uses = [
                {'use': 'personal', 'allowed': True, 'conditions': None},
                {'use': 'commercial', 'allowed': True, 'conditions': ['May be able to register the mark']},
            ]
        else:
            allowed_uses = [
                {'use': 'personal', 'allowed': True, 'conditions': ['Non-commercial reference']},
                {'use': 'commercial', 'allowed': False, 'conditions': ['Would cause brand confusion']},
                {'use': 'descriptive', 'allowed': True, 'conditions': ['Fair use for describing products']},
                {'use': 'parody', 'allowed': True, 'conditions': ['Parody defense may apply']},
            ]
        
        return {
            'content_type': 'trademark',
            'ip_type': 'trademark',
            'status': status,
            'status_text': status_text,
            'status_emoji': emoji,
            'registration_year': registration_year,
            'renewal_period': tm_rules['renewal_period'],
            'indefinite_renewal': tm_rules['indefinite_renewal'],
            'allowed_uses': allowed_uses,
            'jurisdiction': jurisdiction,
            'confidence': 0.7,
            'reasoning': f"Trademarks in {jurisdiction} last {tm_rules['initial_duration']} years but can be renewed indefinitely.",
            'note': "Trademarks don't expire if properly maintained. They protect brand identity, not ideas.",
            'use_requirement': tm_rules.get('use_requirement', True),
        }
    
    # ============ Universal Analyzer ============
    
    def analyze_any(
        self,
        title: str,
        content_type: str,
        creator: Optional[str] = None,
        publication_year: Optional[int] = None,
        jurisdiction: str = "US",
        additional_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Universal analyzer that routes to appropriate method based on content type"""
        
        content_type = (content_type or '').lower()
        
        # Software/Code
        if content_type in ['software', 'code', 'library']:
            return self.analyze_software(
                title=title,
                license_id=additional_data.get('license') if additional_data else None,
                creator=creator,
                publication_year=publication_year,
                additional_data=additional_data
            )
        
        # Patent
        elif content_type == 'patent':
            return self.analyze_patent(
                title=title,
                publication_year=publication_year,
                jurisdiction=jurisdiction,
                additional_data=additional_data
            )
        
        # Trademark
        elif content_type == 'trademark':
            return self.analyze_trademark(
                title=title,
                registration_year=publication_year,
                jurisdiction=jurisdiction,
                additional_data=additional_data
            )
        
        # Traditional copyright (books, music, films, etc.)
        else:
            return self.analyze(
                title=title,
                creator=creator,
                publication_year=publication_year,
                jurisdiction=jurisdiction,
                content_type=content_type,
                **kwargs
            )


# Singleton instance
_rule_engine: Optional[CopyrightRuleEngine] = None


def get_rule_engine() -> CopyrightRuleEngine:
    """Get or create rule engine instance"""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = CopyrightRuleEngine()
    return _rule_engine
