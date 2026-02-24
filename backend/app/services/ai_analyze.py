"""
AI Analysis methods for regulatory updates.
Provides compliance-focused analysis with proper mock fallbacks.
"""

def analyze_update(self, update_title: str, update_summary: str, full_text: str, difficulty_level: str = "professional") -> dict:
    """
    Generates compliance-focused analysis of a regulatory update.
    Returns: {"summary": str, "action_items": list[str], "risk_level": str}
    """
    print(f"[AI SERVICE] Analyzing update with level: {difficulty_level}")
    
    # Determine system prompt based on difficulty level
    system_prompts = {
        "beginner": """You are a pharmaceutical regulatory compliance analyst.

Analyze the provided regulatory update and prepare a summary for executive management.

Requirements:
- Use non-technical language suitable for C-level executives
- Focus on business and operational impact
- Maximum 150 words
- Extract 3-4 clear, actionable compliance steps
- Identify key deadlines and affected departments
- Avoid regulatory jargon; explain terms clearly if used
- Format: Start with impact statement, then action items""",
        
        "professional": """You are a pharmaceutical regulatory compliance analyst.

Analyze the provided regulatory update for compliance professionals.

Requirements:
- Provide detailed regulatory analysis (150-200 words)
- Highlight specific compliance requirements and obligations
- Extract 4-5 actionable compliance steps with measurable outcomes
- Identify impacted processes and systems
- Reference relevant regulatory frameworks (FDA, ICH, etc.) where applicable
- Focus on implementation timeline and resource requirements
- Avoid filler language; be analytical and precise""",
        
        "legal": """You are a pharmaceutical regulatory compliance analyst specializing in legal risk.

Analyze the provided regulatory update for legal and compliance teams.

Requirements:
- Provide comprehensive legal and regulatory analysis (150-200 words)
- Identify legal obligations, liability implications, and enforcement risks
- Extract 5 specific legal/compliance action items with remediation steps
- Highlight potential penalty clauses and non-compliance consequences
- Reference applicable regulations and enforcement history
- Include risk mitigation and documentation requirements
- Be precise, analytical, and legally sound"""
    }
    
    system_prompt = system_prompts.get(difficulty_level, system_prompts["professional"])
    
    # Prepare the content to analyze
    content = f"""REGULATORY UPDATE:

Title: {update_title}

Summary: {update_summary}

Full Details: {full_text[:2000]}

Based on this regulatory update, provide:
1. A concise compliance summary (150-200 words)
2. A JSON array of action items ({"key": "action description"})
3. Risk level: 'Low', 'Medium', or 'High'

Format your response as:
SUMMARY: [compliance summary]
ACTION_ITEMS: ["item1", "item2", ...]
RISK_LEVEL: [High/Medium/Low]"""
    
    # Try to use OpenAI if available
    if self.api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                temperature=0.5,
                max_tokens=1000,
            )
            result_text = response.choices[0].message.content
            print(f"[AI SERVICE] OpenAI response received, parsing...")
            return self._parse_analysis_response(result_text, difficulty_level)
        except Exception as e:
            print(f"[AI SERVICE] OpenAI error: {e}, using mock response")
    
    # Fall back to high-quality mock responses
    return self._generate_mock_analysis(update_title, update_summary, difficulty_level)


def _parse_analysis_response(self, response_text: str, difficulty_level: str) -> dict:
    """Parse the structured response from LLM."""
    try:
        summary = ""
        action_items = []
        risk_level = "Medium"
        
        # Extract summary
        if "SUMMARY:" in response_text:
            summary_start = response_text.find("SUMMARY:") + 8
            summary_end = response_text.find("ACTION_ITEMS:")
            summary = response_text[summary_start:summary_end].strip()
        
        # Extract action items
        if "ACTION_ITEMS:" in response_text:
            items_start = response_text.find("ACTION_ITEMS:") + 13
            items_end = response_text.find("RISK_LEVEL:")
            items_text = response_text[items_start:items_end].strip()
            # Parse JSON array
            import json
            try:
                action_items = json.loads(items_text)
                if isinstance(action_items, dict):
                    action_items = [f"{k}: {v}" for k, v in action_items.items()]
            except:
                # Fallback: split by commas
                action_items = [item.strip().strip('"').strip('-').strip('•') for item in items_text.split(',')]
        
        # Extract risk level
        if "RISK_LEVEL:" in response_text:
            risk_start = response_text.find("RISK_LEVEL:") + 11
            risk_text = response_text[risk_start:].split('\n')[0].strip()
            if "high" in risk_text.lower():
                risk_level = "High"
            elif "low" in risk_text.lower():
                risk_level = "Low"
            else:
                risk_level = "Medium"
        
        return {
            "summary": summary if summary else response_text[:500],
            "action_items": action_items[:5],
            "risk_level": risk_level
        }
    except Exception as e:
        print(f"[AI SERVICE] Parse error: {e}")
        return {
            "summary": response_text[:400],
            "action_items": ["Review full update", "Assess impact", "Implement changes"],
            "risk_level": "Medium"
        }


def _generate_mock_analysis(self, title: str, summary: str, difficulty_level: str) -> dict:
    """Generate high-quality mock analysis when LLM is unavailable."""
    title_lower = title.lower()
    summary_lower = summary.lower()
    combined_text = f"{title_lower} {summary_lower}"
    
    # Detect update type and severity
    is_approval = "approv" in combined_text or "approved" in combined_text
    is_safety = "safety" in combined_text or "adverse" in combined_text or "risk" in combined_text
    is_manufacturing = "manufacturing" in combined_text or "facility" in combined_text or "gmp" in combined_text
    is_guidance = "guidance" in combined_text or "recommend" in combined_text
    is_urgent = "recall" in combined_text or "urgent" in combined_text or "immediate" in combined_text
    
    risk_level = "High" if (is_safety and is_urgent) or "recall" in combined_text else ("Medium" if is_safety or is_manufacturing else "Low")
    
    if difficulty_level == "beginner":
        if is_approval:
            return {
                "summary": "A new product or indication has received regulatory approval. The organization should review the approved product characteristics, monitor market entry, and assess competitive impacts. Key stakeholders should be briefed on implications for current product portfolios and strategy.",
                "action_items": ["Brief executive team on approval", "Monitor market availability", "Update competitive analysis"],
                "risk_level": "Low"
            }
        elif is_safety:
            return {
                "summary": "A safety issue has been identified with a regulatory product. Immediate review of company products and manufacturing is required to ensure compliance. If applicable, corrective actions must be implemented promptly to protect patient safety and maintain regulatory standing.",
                "action_items": ["Evaluate company product exposure", "Assess manufacturing processes", "Implement corrective actions", "Report to regulatory authorities if required"],
                "risk_level": risk_level
            }
        else:
            return {
                "summary": "The regulatory authority has issued new guidance or requirements. Compliance is mandatory. The organization must review requirements, assess current practices, and implement necessary changes within regulatory timeframes to remain compliant.",
                "action_items": ["Review new requirements", "Assess current compliance", "Develop implementation plan"],
                "risk_level": "Medium"
            }
    
    elif difficulty_level == "professional":
        if is_approval:
            return {
                "summary": "Regulatory authority has approved a new product or therapeutic indication. This marks a significant milestone in development and market access. The approval decision defines approved indications, patient populations, dosing regimens, and postapproval commitments. Organizations should conduct comprehensive competitive and market analysis, establish pharmacovigilance monitoring, and coordinate commercial, medical, and regulatory strategies for product launch and lifecycle management.",
                "action_items": [
                    "Conduct expedited competitive benchmarking and market opportunity assessment",
                    "Establish pharmacovigilance and adverse event monitoring systems",
                    "Ensure labeling compliance and promotional material review",
                    "Develop risk management and post-approval commitment fulfillment plans",
                    "Coordinate cross-functional launch strategy and timeline"
                ],
                "risk_level": "Low"
            }
        elif is_safety:
            return {
                "summary": "Regulatory authority has identified a safety signal, adverse event pattern, or manufacturing compliance concern. Depending on severity, may trigger recalls, import alerts, or mandatory corrective actions. Organizations must immediately assess exposure to affected products, manufacturing batches, and suppliers. Comprehensive risk assessment is required to determine evidence strength, affected patient populations, and required interventions. All findings must be documented and reported to regulatory authorities as appropriate.",
                "action_items": [
                    "Conduct immediate inventory assessment and traceability review for affected products",
                    "Perform comprehensive safety and efficacy data review for company products",
                    "Evaluate manufacturing controls and implement enhanced quality monitoring",
                    "Develop and execute remediation plan with regulatory timeline expectations",
                    "Submit adverse event reports and corrective action notifications as required"
                ],
                "risk_level": risk_level
            }
        else:
            return {
                "summary": "Regulatory authority has issued updated guidance, policy, or requirements. Compliance is mandatory and must be demonstrated upon inspection or audit. Organizations should conduct gap analysis of current practices against new requirements, prioritize implementation based on regulatory enforcement timing, and develop comprehensive compliance strategy. Implementation must address documentation, training, process changes, and internal audit/verification.",
                "action_items": [
                    "Perform detailed compliance gap analysis against new regulatory requirements",
                    "Prioritize implementation based on regulatory enforcement priorities and timelines",
                    "Develop comprehensive standard operating procedure updates",
                    "Implement staff training and competency verification programs",
                    "Establish internal audit and compliance verification processes"
                ],
                "risk_level": "Medium"
            }
    
    else:  # legal
        if is_approval:
            return {
                "summary": "Regulatory authority approval establishes legal authorization for product manufacture, distribution, and marketing within specific approved parameters. Approval defines the legal scope of permissible claims, indications, and patient populations. Organizations must maintain strict compliance with approved labeling and promotional restrictions to avoid regulatory action, warning letters, consent decrees, or civil/criminal liability. Any deviation from approved parameters constitutes regulatory non-compliance and product misbranding.",
                "action_items": [
                    "Establish legal and compliance framework for approved indication and labeling restrictions",
                    "Implement promotional material governance and pre-approval review procedures",
                    "Develop legal documentation standards for all marketing and distribution activities",
                    "Establish liability management and insurance requirements",
                    "Create audit and monitoring procedures to ensure ongoing compliance with approval terms"
                ],
                "risk_level": "Low"
            }
        elif is_safety:
            return {
                "summary": "Safety concerns trigger multiple legal and compliance obligations: mandatory reporting to regulatory authorities, potential product liability exposure, informed consent and disclosure requirements, and possible criminal liability if negligence is demonstrated. Warning letters, consent decrees, recalls, or class action litigation may result from non-compliance. All safety findings must be immediately documented and reported; failure to report constitutes additional regulatory violations and increases legal exposure. Organizations face penalties ranging from fines to criminal prosecution depending on severity and failure to act.",
                "action_items": [
                    "Immediately document all safety findings and establish evidence preservation procedures",
                    "Assess legal liability exposure and notification obligations to patients/providers",
                    "File required adverse event reports and safety notifications within regulatory timeframes",
                    "Coordinate with legal counsel on litigation risk assessment and insurance notification",
                    "Implement injunctive relief procedures if product recall or import alert is imminent"
                ],
                "risk_level": "High"
            }
        else:
            return {
                "summary": "Regulatory guidance establishes authorities' enforcement expectations and creates legal obligations for industry compliance. Non-compliance creates multiple legal risks: regulatory enforcement action, warning letters, consent decrees, civil money penalties, product seizures, and debarment. Public enforcement history demonstrates authorities' administrative and judicial enforcement capacity. Organizations must establish legal compliance documentation and demonstrate knowing, willful adherence to regulatory requirements or face enhanced penalties for negligence or misconduct.",
                "action_items": [
                    "Establish written legal compliance policies reflecting regulatory guidance requirements",
                    "Certify organizational compliance through documented management review and attestation",
                    "Implement legal audit and surveillance procedures with professional documentation",
                    "Establish regulatory liaison and legal reporting procedures for non-compliance discovery",
                    "Maintain compliance insurance and establish legal defense preparedness"
                ],
                "risk_level": "Medium"
            }
