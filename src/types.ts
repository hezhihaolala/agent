export type VerificationStatus = 'verified' | 'unverified' | 'conflicting'
export type Gender = 'male' | 'female' | 'unknown'

export type Person = {
  id: string
  name: string
  gender: Gender
  birth_date: string | null
  death_date: string | null
  native_place: string | null
  biography: string | null
  verification_status: VerificationStatus
  created_at: string
  updated_at: string
}

export type Relationship = {
  id: string
  kind: 'parent' | 'spouse' | 'sibling' | 'paternal_cousin'
  person_id: string
  relative_id: string
  verification_status: VerificationStatus
  created_at: string
}

export type Source = {
  id: string
  title: string
  source_type: 'image' | 'document' | 'text'
  era: string | null
  provenance: string | null
  notes: string | null
  verification_status: VerificationStatus
  original_filename: string
  media_type: string
  size_bytes: number
  sha256: string
  created_at: string
}

export type AuditLog = {
  id: string
  action: string
  entity_type: string
  entity_id: string
  summary: string
  created_at: string
}

export type Kinship = {
  label: string
  steps: Array<{ person_id: string; person_name: string }>
}

export type AgentAnswer = {
  type: 'answer'
  answer: string
  relationship: Kinship
  sources: Array<Pick<Source, 'id' | 'title' | 'verification_status'>>
  verification_status: VerificationStatus
}

export type RelativeListAnswer = {
  type: 'relative_list'
  answer: string
  relation_type: 'parents' | 'father' | 'mother' | 'children' | 'spouses' | 'siblings' | 'paternal_cousins'
  relationships: Kinship[]
  sources: Array<Pick<Source, 'id' | 'title' | 'verification_status'>>
  verification_status: VerificationStatus
}

export type DraftPreview = {
  type: 'draft'
  draft_id: string
  status: 'pending'
  summary: string
  payload: {
    operation: 'create_person' | 'create_child'
    person: { name: string; gender: Gender }
    parent_id?: string
    parent_name?: string
  }
}

export type AnswerResult = AgentAnswer | RelativeListAnswer
export type AgentResult = AnswerResult | DraftPreview
