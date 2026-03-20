"""
AI Service using Groq API with Llama 3 Model
Handles RAG responses and general LLM queries with improved logging
"""
import os
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# Load .env from backend first, then from repo root if present
_SERVICE_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SERVICE_DIR.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_ROOT_DIR / ".env")


class AIService:
    """
    AI Service powered by Groq API with Llama 3-70b model
    Supports RAG mode (with database context) and general knowledge mode
    """
    
    def __init__(self):
        """Initialize Groq client"""
        self.api_key = os.getenv("GROQ_API_KEY")
        print(f"[AI SERVICE] GROQ_API_KEY present: {bool(self.api_key)}")
        print(f"[AI SERVICE] API Key prefix: {self.api_key[:20] if self.api_key else 'None'}...")
        
        if not self.api_key:
            print("[AI SERVICE] ERROR: GROQ_API_KEY not found in environment")
            self.client = None
        else:
            try:
                self.client = Groq(api_key=self.api_key)
                print("[AI SERVICE] ✓ Groq client initialized successfully")
            except Exception as e:
                print(f"[AI SERVICE] ERROR initializing Groq: {e}")
                import traceback
                traceback.print_exc()
                self.client = None
        
        # System prompt for pharmaceutical regulatory assistant
        self.system_prompt = """You are a pharmaceutical regulatory intelligence assistant specializing in FDA, EMA, MHRA, PMDA, CDSCO, NMPA, and ICH regulations.

Your role:
- Answer questions about pharmaceutical regulations and guidelines
- Use database context when provided (RAG mode)
- Provide general regulatory knowledge when no context available
- Deliver structured, concise responses (100-200 words)
- Be accurate and cite specific details from documents

Response format:
- Main heading in bold
- 2-3 key bullet points
- Specific facts only (no generic theory)"""

    def generate_smart_answer(
        self,
        query: str,
        context: str = "",
        intent: str = "GENERAL_KNOWLEDGE",
        detected_authority: Optional[str] = None,
        retrieval_metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate AI response using Groq Llama 3 model
        
        Args:
            query: User's question
            context: Retrieved documents (if RAG mode)
            intent: Query intent type
            detected_authority: Authority detected in query (FDA, EMA, etc.)
            retrieval_metrics: Metrics from RAG retrieval
            
        Returns:
            Generated answer string
        """
        print(f"\n[AI SERVICE] === generate_smart_answer called ===")
        print(f"[AI SERVICE] Query: {query[:80]}...")
        print(f"[AI SERVICE] Intent: {intent}")
        print(f"[AI SERVICE] Detected Authority: {detected_authority}")
        print(f"[AI SERVICE] Context length: {len(context)} chars")
        print(f"[AI SERVICE] Client available: {self.client is not None}")
        
        # Log retrieval metrics
        if retrieval_metrics:
            print(f"[AI SERVICE] Retrieval metrics: {retrieval_metrics}")
        
        # Check if we have valid Groq client
        if not self.client:
            print("[AI SERVICE] ⚠️  No Groq client available - using fallback")
            return self._generate_fallback_answer(query, context, intent, detected_authority)
        
        try:
            # Determine mode: RAG or General Knowledge
            if context.strip() and retrieval_metrics and retrieval_metrics.get("documents_injected", 0) > 0:
                mode = "RAG"
                print(f"[AI SERVICE] MODE: RAG (injecting {retrieval_metrics['documents_injected']} documents)")
                user_message = self._build_rag_prompt(query, context, detected_authority, retrieval_metrics)
            else:
                mode = "GENERAL_KNOWLEDGE"
                print(f"[AI SERVICE] MODE: GENERAL_KNOWLEDGE (no document injection)")
                user_message = self._build_general_prompt(query, detected_authority)
            
            # Log prompt details
            print(f"[AI SERVICE] User message length: {len(user_message)} chars")
            print(f"[AI SERVICE] Calling Groq API (model: llama-3.3-70b-versatile)...")
            
            # Call Groq API
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.3 if mode == "RAG" else 0.7,
                max_tokens=800,
                top_p=1,
                stream=False
            )
            
            answer = chat_completion.choices[0].message.content
            print(f"[AI SERVICE] ✓ Response received: {len(answer)} chars")
            print(f"[AI SERVICE] Finish reason: {chat_completion.choices[0].finish_reason}")
            print(f"[AI SERVICE] Tokens used: {chat_completion.usage.total_tokens if chat_completion.usage else 'N/A'}")
            
            return answer
            
        except Exception as e:
            print(f"[AI SERVICE] ❌ Groq API error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"[AI SERVICE] Falling back to static response")
            return self._generate_fallback_answer(query, context, intent, detected_authority)

    def _build_rag_prompt(
        self,
        query: str,
        context: str,
        authority: Optional[str],
        metrics: Dict[str, Any]
    ) -> str:
        """
        Build prompt for RAG mode (with retrieved documents)
        """
        authority_str = authority if authority else "Multiple authorities"
        num_docs = metrics.get("documents_injected", 0)
        
        prompt = f"""Query: {query}

Detected Authority: {authority_str}

Retrieved Documents ({num_docs} documents from database):
---
{context}
---

Instructions:
1. Answer the user's question using ONLY the information from the documents above
2. Synthesize information from multiple documents if relevant
3. Cite specific details (dates, authorities, key points)
4. Keep response concise (100-200 words)
5. If documents don't fully answer the question, acknowledge limitations

Provide a structured, professional response based on these documents."""
        
        return prompt

    def _build_general_prompt(
        self,
        query: str,
        authority: Optional[str]
    ) -> str:
        """
        Build prompt for general knowledge mode (no documents)
        """
        authority_str = f" regarding {authority}" if authority else ""
        
        prompt = f"""Query: {query}

Context: No specific documents were retrieved from the database{authority_str}.

Instructions:
1. Answer using your general knowledge of pharmaceutical regulations
2. Provide accurate, factual information about regulatory processes
3. Keep response concise (100-200 words)
4. Structure with clear headings and bullet points
5. Acknowledge if you're providing general information vs. specific updates
6. Suggest where users can find official information

Provide a helpful, structured response using general regulatory knowledge."""
        
        return prompt

    def _generate_fallback_answer(
        self,
        query: str,
        context: str,
        intent: str,
        authority: Optional[str] = None
    ) -> str:
        """
        Generate static fallback response when Groq API unavailable
        """
        print("[AI SERVICE] Generating fallback static response")
        
        query_lower = query.lower()
        authority_name = authority if authority else "regulatory authorities"
        
        # If we have context (documents), acknowledge them
        if context.strip():
            return f"""**{authority_name.upper()} Information**

Based on retrieved regulatory documents:

• Key regulatory requirements and guidelines applicable to your query
• Specific compliance timelines and implementation details
• Official documentation and reference materials

**Note:** AI service temporarily unavailable. This response is based on document retrieval only. For detailed analysis, please retry or consult official {authority_name} sources directly.

**Recommended Action:** Check official {authority_name} website for complete information."""
        
        # General knowledge responses for common queries
        if "fda" in query_lower or "approval" in query_lower:
            return """**FDA Regulatory Overview**

The FDA (Food and Drug Administration) regulates:

• **Drug Approval:** IND → NDA/BLA submission → FDA review → Market authorization
• **Key Requirements:** Clinical data, safety profile, manufacturing compliance
• **Timeline:** Typically 10-12 months for standard review, 6 months for priority

**Official Resources:**
- FDA.gov for current guidelines
- Drugs@FDA database for approved products
- CDER for drug-specific regulations

**Note:** For current updates and specific guidance, consult FDA official channels."""
        
        elif "ema" in query_lower:
            return """**EMA Regulatory Overview**

The European Medicines Agency (EMA) provides:

• **Centralized Procedure:** Single marketing authorization valid across EU
• **Key Requirements:** Quality, safety, efficacy dossiers (CTD format)
• **CHMP Review:** Scientific assessment by Committee for Medicinal Products

**Official Resources:**
- EMA.europa.eu for guidelines
- EU Clinical Trials Register
- Eudralex for EU pharmaceutical legislation

**Note:** For current updates and specific guidance, consult EMA official channels."""
        
        elif "gmp" in query_lower or "manufacturing" in query_lower:
            return """**GMP (Good Manufacturing Practice) Overview**

Key GMP requirements for pharmaceutical manufacturing:

• **Facility Standards:** Controlled environments, validated equipment
• **Personnel:** Trained staff, documented procedures
• **Quality Control:** Batch testing, release procedures
• **Documentation:** Complete records, deviation management

**Applicable Standards:**
- FDA: 21 CFR Parts 210 & 211
- EMA: Eudralex Volume 4
- ICH Q7: Active Pharmaceutical Ingredients

**Note:** For specific GMP requirements, consult authority-specific guidelines."""
        
        elif "clinical trial" in query_lower:
            return """**Clinical Trials Regulatory Framework**

Regulatory requirements for clinical trials:

• **Phase I-III:** Safety, efficacy, dosing studies
• **IND/CTA:** Regulatory approval before starting trials
• **GCP Compliance:** Good Clinical Practice standards (ICH E6)
• **Ethics Review:** IRB/EC approval mandatory

**Key Regulations:**
- FDA: 21 CFR Parts 50, 56, 312
- EMA: Clinical Trials Regulation (EU) No 536/2014
- ICH GCP guidelines

**Note:** For current trial requirements, consult relevant regulatory authority."""
        
        else:
            # Generic regulatory response
            return f"""**Regulatory Intelligence Response**

Based on your query regarding {authority_name}:

• Pharmaceutical regulations ensure safety, efficacy, and quality of medicinal products
• Specific requirements vary by region (FDA, EMA, MHRA, PMDA, etc.)
• Compliance requires understanding current guidelines and implementation timelines

**Recommended Actions:**
1. Identify applicable regulatory authority
2. Review official guidelines and regulations
3. Consult regulatory professionals for specific compliance questions

**Note:** For current, authoritative information, always refer to official regulatory body websites and published guidance documents."""

    def analyze_update(
        self,
        update_title: str,
        update_summary: str,
        full_text: str,
        difficulty_level: str = "professional"
    ) -> dict:
        """
        Generates compliance-focused analysis of a regulatory update using Groq.
        
        Args:
            update_title: Title of the regulatory update
            update_summary: Short summary of the update
            full_text: Full text content of the update
            difficulty_level: One of "beginner", "professional", or "legal"
            
        Returns:
            dict with keys: "summary" (str), "action_items" (list[str]), "risk_level" (str)
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
2. A JSON array of action items
3. Risk level: 'Low', 'Medium', or 'High'

Format your response as:
SUMMARY: [compliance summary]
ACTION_ITEMS: ["item1", "item2", ...]
RISK_LEVEL: [High/Medium/Low]"""
        
        # Try to use Groq if available
        if self.client:
            try:
                print(f"[AI SERVICE] Calling Groq for update analysis...")
                response = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content}
                    ],
                    temperature=0.5,
                    max_tokens=1000,
                )
                result_text = response.choices[0].message.content
                print(f"[AI SERVICE] ✓ Groq analysis response received, parsing...")
                return self._parse_analysis_response(result_text, difficulty_level)
            except Exception as e:
                print(f"[AI SERVICE] ❌ Groq error: {e}, using mock response")
                import traceback
                traceback.print_exc()
        
        # Fall back to high-quality mock responses
        print(f"[AI SERVICE] ⚠️  No Groq client, using mock analysis")
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
                if summary_end == -1:
                    summary_end = len(response_text)
                summary = response_text[summary_start:summary_end].strip()
            
            # Extract action items
            if "ACTION_ITEMS:" in response_text:
                items_start = response_text.find("ACTION_ITEMS:") + 13
                items_end = response_text.find("RISK_LEVEL:")
                if items_end == -1:
                    items_end = len(response_text)
                items_text = response_text[items_start:items_end].strip()
                # Parse JSON array
                import json
                try:
                    action_items = json.loads(items_text)
                    if isinstance(action_items, dict):
                        action_items = [f"{k}: {v}" for k, v in action_items.items()]
                except:
                    # Fallback: split by commas or newlines
                    action_items = [
                        item.strip().strip('"').strip('-').strip('•').strip()
                        for item in items_text.replace('\n', ',').split(',')
                        if item.strip()
                    ][:5]
            
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
                "action_items": action_items[:5] if action_items else ["Review full update", "Assess impact", "Implement changes"],
                "risk_level": risk_level
            }
        except Exception as e:
            print(f"[AI SERVICE] ❌ Parse error: {e}")
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
                    "summary": "Regulatory authority has identified a safety signal, adverse event pattern, or manufacturing compliance concern. Depending on severity, may trigger recalls, import alerts, or mandatory corrective actions. Organizations must immediately assess exposure to affected products, manufacturing batches, and suppliers. Comprehensive risk assessment is required to determine evidence strength, affected patient populations, and required interventions.",
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
                    "summary": "Regulatory authority has issued updated guidance, policy, or requirements. Compliance is mandatory and must be demonstrated upon inspection or audit. Organizations should conduct gap analysis of current practices against new requirements, prioritize implementation based on regulatory enforcement timing, and develop comprehensive compliance strategy.",
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
                    "summary": "Regulatory authority approval establishes legal authorization for product manufacture, distribution, and marketing within specific approved parameters. Approval defines the legal scope of permissible claims, indications, and patient populations. Organizations must maintain strict compliance with approved labeling and promotional restrictions to avoid regulatory action.",
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
                    "summary": "Safety concerns trigger multiple legal and compliance obligations: mandatory reporting to regulatory authorities, potential product liability exposure, informed consent and disclosure requirements. All safety findings must be immediately documented and reported; failure to report constitutes additional regulatory violations and increases legal exposure.",
                    "action_items": [
                        "Immediately document all safety findings and establish evidence preservation procedures",
                        "Assess legal liability exposure and notification obligations to patients/providers",
                        "File required adverse event reports and safety notifications within regulatory timeframes",
                        "Coordinate with legal counsel on litigation risk assessment and insurance notification",
                        "Implement remediation procedures if product recall or corrective action is required"
                    ],
                    "risk_level": "High"
                }
            else:
                return {
                    "summary": "Regulatory guidance establishes authorities' enforcement expectations and creates legal obligations for industry compliance. Non-compliance creates multiple legal risks: regulatory enforcement action, warning letters, consent decrees, civil money penalties, and product seizures. Organizations must establish legal compliance documentation and demonstrate adherence to regulatory requirements.",
                    "action_items": [
                        "Establish written legal compliance policies reflecting regulatory guidance requirements",
                        "Certify organizational compliance through documented management review and attestation",
                        "Implement legal audit and surveillance procedures with professional documentation",
                        "Establish regulatory liaison and legal reporting procedures for non-compliance discovery",
                        "Maintain compliance records and establish legal defense preparedness"
                    ],
                    "risk_level": "Medium"
                }


# Global instance
ai_service = AIService()
