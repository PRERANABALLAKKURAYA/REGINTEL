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
                print("[AI SERVICE] Groq client initialized successfully")
            except Exception as e:
                print(f"[AI SERVICE] ERROR initializing Groq: {e}")
                import traceback
                traceback.print_exc()
                self.client = None
        
        # System prompt template (formatted per request with query + context)
        self.system_prompt_template = """You are a Regulatory Intelligence Assistant.

User Query: {query}
Context: {context}
Query Mode: {query_mode}
Detected Authority: {authority}

Instructions:
- Identify regulatory authority mentioned (FDA, EMA, ICH, etc.)
- Focus ONLY on that authority unless comparison is explicitly asked
- If query includes "latest" or "recent":
    - Prioritize recent regulatory updates, guidelines, or policy changes
    - Mention years or document names if possible
- DO NOT give general textbook explanations unless no data exists
- If context is available:
    - Use it FIRST
    - Extract specific facts
- If context is missing:
    - Use domain knowledge BUT stay specific to authority

Response Format (always):
Title: <one-line answer title>
Key Points:
- <point 1>
- <point 2>
- <point 3>
Latest Updates:
1. <latest item or trend>
2. <latest item or trend>
Actionable Insights:
- <action 1>
- <action 2>
Sources:
- <source name or URL if available>

Formatting Rules:
- No markdown symbols such as **, ###, or fenced blocks
- Keep sections readable with blank lines
- If latest updates are unavailable, provide best current guidance in Latest Updates section
- Never output generic failure statements such as AI unavailable or no data found""" 

    def generate_smart_answer(
        self,
        query: str,
        context: str = "",
        intent: str = "GENERAL_KNOWLEDGE",
        detected_authority: Optional[str] = None,
        query_mode: str = "standard",
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
        print(f"[AI SERVICE] Query Mode: {query_mode}")
        print(f"[AI SERVICE] Context length: {len(context)} chars")
        print(f"[AI SERVICE] Client available: {self.client is not None}")
        
        # Log retrieval metrics
        if retrieval_metrics:
            print(f"[AI SERVICE] Retrieval metrics: {retrieval_metrics}")
        
        # Check if we have valid Groq client
        if not self.client:
            print("[AI SERVICE] No Groq client available - using fallback")
            return self._generate_fallback_answer(query, context, intent, detected_authority, query_mode)
        
        try:
            # Build request-specific system prompt with injected query/context
            context_for_prompt = context.strip() if context and context.strip() else "No additional context provided."
            system_prompt = self.system_prompt_template.format(
                query=query.strip(),
                context=context_for_prompt,
                query_mode=query_mode,
                authority=detected_authority or "Not specified"
            )

            # Determine mode: RAG or General Knowledge
            if context.strip() and retrieval_metrics and retrieval_metrics.get("documents_injected", 0) > 0:
                mode = "RAG"
                print(f"[AI SERVICE] MODE: RAG (injecting {retrieval_metrics['documents_injected']} documents)")
                user_message = self._build_rag_prompt(query, context, detected_authority, query_mode, retrieval_metrics)
            else:
                mode = "GENERAL_KNOWLEDGE"
                print(f"[AI SERVICE] MODE: GENERAL_KNOWLEDGE (no document injection)")
                user_message = self._build_general_prompt(query, detected_authority, query_mode)
            
            # Log prompt details
            print(f"[AI SERVICE] User message length: {len(user_message)} chars")
            print(f"[AI SERVICE] Calling Groq API (model: llama-3.3-70b-versatile)...")
            
            # Call Groq API
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.3 if mode == "RAG" else 0.7,
                max_tokens=800,
                top_p=1,
                stream=False
            )
            
            answer = chat_completion.choices[0].message.content
            print(f"[AI SERVICE] Response received: {len(answer)} chars")
            print(f"[AI SERVICE] Finish reason: {chat_completion.choices[0].finish_reason}")
            print(f"[AI SERVICE] Tokens used: {chat_completion.usage.total_tokens if chat_completion.usage else 'N/A'}")
            
            return self._normalize_response(answer)
            
        except Exception as e:
            print(f"[AI SERVICE] Groq API error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"[AI SERVICE] Falling back to static response")
            return self._generate_fallback_answer(query, context, intent, detected_authority, query_mode)

    def _normalize_response(self, answer: str) -> str:
        """Normalize model output to clean UI-friendly structured format."""
        cleaned = (answer or "").replace("**", "").replace("###", "").replace("##", "").strip()

        # If required sections already exist, return cleaned content.
        required = ["Title:", "Key Points:", "Latest Updates:", "Actionable Insights:", "Sources:"]
        if all(section in cleaned for section in required):
            return cleaned

        lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
        title = lines[0] if lines else "Regulatory Guidance Summary"

        key_points = []
        for ln in lines[1:]:
            if len(key_points) >= 4:
                break
            if ln and not ln.lower().startswith(("title:", "key points:", "latest updates:", "actionable insights:", "sources:")):
                key_points.append(ln.lstrip("- "))

        if not key_points:
            key_points = ["Regulatory requirements should be interpreted in the context of authority-specific pathways."]

        latest_updates = ["Recent authority-relevant guidance should be prioritized by publication date and scope."]
        actionable = [
            "Map guidance points to dossier sections, quality controls, and lifecycle obligations.",
            "Create an implementation tracker with owners and deadlines for compliance execution.",
        ]
        sources = ["Regulatory context and retrieved authority data"]

        return self._build_structured_response(title, key_points, latest_updates, actionable, sources)

    def _build_structured_response(
        self,
        title: str,
        key_points: list[str],
        latest_updates: list[str],
        actionable: list[str],
        sources: list[str],
    ) -> str:
        def _list(items: list[str], bullet: str = "-") -> str:
            if not items:
                return f"{bullet} Not available"
            return "\n".join([f"{bullet} {item}" for item in items])

        numbered_updates = "\n".join([f"{i + 1}. {item}" for i, item in enumerate(latest_updates or ["Best current guidance has been provided based on available evidence."])])

        return (
            f"Title: {title}\n\n"
            f"Key Points:\n{_list(key_points)}\n\n"
            f"Latest Updates:\n{numbered_updates}\n\n"
            f"Actionable Insights:\n{_list(actionable)}\n\n"
            f"Sources:\n{_list(sources)}"
        )

    def _build_rag_prompt(
        self,
        query: str,
        context: str,
        authority: Optional[str],
        query_mode: str,
        metrics: Dict[str, Any]
    ) -> str:
        """
        Build prompt for RAG mode (with retrieved documents)
        """
        authority_str = authority if authority else "Multiple authorities"
        num_docs = metrics.get("documents_injected", 0)
        
        prompt = f"""Use this context first and answer naturally.

    Query: {query}
    Detected Authority: {authority_str}
    Query Mode: {query_mode}
    Documents Retrieved: {num_docs}

    Context:
    ---
    {context}
    ---

    Answer with practical regulatory interpretation, specific references where relevant, and region differences only if they help the user."""
        
        return prompt

    def _build_general_prompt(
        self,
        query: str,
        authority: Optional[str],
        query_mode: str
    ) -> str:
        """
        Build prompt for general knowledge mode (no documents)
        """
        authority_str = f" regarding {authority}" if authority else ""
        
        prompt = f"""Query: {query}
    Query Mode: {query_mode}

    No high-confidence document context was retrieved{authority_str}.

    Provide a direct, expert answer using domain knowledge while staying specific to the detected authority. Avoid generic textbook phrasing and avoid cross-authority comparisons unless requested."""
        
        return prompt

    def _generate_fallback_answer(
        self,
        query: str,
        context: str,
        intent: str,
        authority: Optional[str] = None,
        query_mode: str = "standard"
    ) -> str:
        """Generate deterministic structured answer when LLM call cannot be completed."""
        print("[AI SERVICE] Generating deterministic structured fallback response")

        query_lower = query.lower()
        authority_name = authority if authority else "relevant authority"

        if context.strip():
            lines = [line.strip() for line in context.splitlines() if line.strip()]
            condensed = []
            source_urls = []
            for line in lines:
                if line.startswith("Title:") or line.startswith("Authority:") or line.startswith("Date:") or line.startswith("Category:"):
                    condensed.append(line)
                if line.startswith("Source:"):
                    source_urls.append(line.replace("Source:", "").strip())
                if len(condensed) >= 8:
                    break

            key_points = condensed if condensed else ["Relevant authority context was retrieved and considered."]
            latest_updates = ["Prioritize the most recent dated items in the retrieved context."]
            actionable = [
                "Translate key guidance into submission and lifecycle control actions.",
                "Assign owners and timelines for implementation readiness.",
            ]
            sources = source_urls if source_urls else [f"Retrieved context for {authority_name}"]
            return self._build_structured_response(
                title=f"{authority_name} regulatory guidance overview",
                key_points=key_points[:5],
                latest_updates=latest_updates,
                actionable=actionable,
                sources=sources,
            )

        if "biosimilar" in query_lower or "biosimilar" in query_lower:
            prefix = f"No recent {authority}-specific updates found. Here is the most relevant current guidance:\n\n" if query_mode == "latest" and authority else ""
            key_points = [
                "Biosimilar assessment follows a totality-of-evidence approach with analytical similarity as the foundation.",
                "FDA 351(k) pathway emphasizes residual uncertainty reduction through targeted nonclinical and clinical evidence.",
                "Comparability principles such as ICH Q5E are practical for post-change similarity logic.",
            ]
            latest_updates = [
                f"{authority_name} latest biosimilar guidance should be prioritized by publication year and scope.",
            ]
            actionable = [
                "Build the development plan around analytical comparability first.",
                "Justify any reduced clinical package with explicit residual uncertainty rationale.",
            ]
            sources = [f"{authority_name} biosimilar guidance framework"]
            title = "Biosimilar guidance summary"
            if prefix:
                latest_updates.insert(0, prefix.strip())
            return self._build_structured_response(title, key_points, latest_updates, actionable, sources)

        if "stability" in query_lower or "zone iv" in query_lower:
            return (
                "For stability strategy, anchor on ICH Q1A(R2) and regional implementation details.\n\n"
                "Key insights:\n"
                "- Long-term and accelerated conditions should support shelf-life and label storage statements.\n"
                "- Zone IV programs often require hot/humid condition coverage and packaging-performance evidence.\n"
                "- FDA and EMA expectations are broadly aligned to ICH, but filing practices and deficiency focus can differ by review division and product type.\n\n"
                "Practical interpretation: pre-empt review questions by linking stability trends to specification strategy, transport stress, and container closure performance."
            )

        if "clinical trial" in query_lower or "gcp" in query_lower:
            return (
                "Clinical trial compliance should be framed around ICH E6(R2/R3 transition), informed consent controls, and safety reporting governance.\n\n"
                "Key insights:\n"
                "- FDA: 21 CFR Parts 50, 56, 312 remain core for drug trials.\n"
                "- EU/EMA environment: CTR 536/2014 operational requirements affect submissions and transparency workflows.\n"
                "- Risk-based quality management is expected in modern GCP operations.\n\n"
                "Practical interpretation: align protocol deviations, vendor oversight, and pharmacovigilance interfaces before first-patient-in to avoid inspection findings."
            )

        if query_mode == "latest" and authority:
            return (
                f"No recent {authority}-specific updates found. Here is the most relevant current guidance:\n\n"
                f"For {authority}, focus on the most recent applicable guidance framework tied to your query, then map requirements to submission content, lifecycle controls, and post-approval obligations.\n\n"
                "Practical implications:\n"
                "- Confirm the governing pathway and legal basis first.\n"
                "- Translate guidance into actionable dossier sections and evidence requirements.\n"
                "- Prioritize implementation by compliance risk and submission timelines."
            )

        return self._build_structured_response(
            title="Regulatory guidance summary",
            key_points=[
                f"Query scope: {query}",
                "Identify governing regulations and authority-specific implementation requirements.",
                "Prioritize obligations that affect submission content, CMC controls, labeling, and post-approval commitments.",
            ],
            latest_updates=["Use the most recently available authority guidance and policy updates relevant to this topic."],
            actionable=[
                "Convert guidance requirements into a compliance action plan with owners and timelines.",
                "Prepare evidence artifacts for audit and submission readiness.",
            ],
            sources=[f"{authority_name} regulatory framework"],
        )

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
                print(f"[AI SERVICE] Groq analysis response received, parsing...")
                return self._parse_analysis_response(result_text, difficulty_level)
            except Exception as e:
                print(f"[AI SERVICE] Groq error: {e}, using mock response")
                import traceback
                traceback.print_exc()
        
        # Fall back to high-quality mock responses
        print(f"[AI SERVICE] No Groq client, using mock analysis")
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
