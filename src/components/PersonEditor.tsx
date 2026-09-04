import { FormEvent, useState } from 'react'
import { api } from '../api'
import type { Gender, Person, VerificationStatus } from '../types'

export function PersonEditor({ person, onSaved, onClose }: { person?: Person; onSaved: () => Promise<void>; onClose: () => void }) {
  const [name, setName] = useState(person?.name ?? '')
  const [gender, setGender] = useState<Gender>(person?.gender ?? 'unknown')
  const [birthDate, setBirthDate] = useState(person?.birth_date ?? '')
  const [nativePlace, setNativePlace] = useState(person?.native_place ?? '')
  const [biography, setBiography] = useState(person?.biography ?? '')
  const [status, setStatus] = useState<VerificationStatus>(person?.verification_status ?? 'unverified')
  const [error, setError] = useState('')

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    const payload = { name, gender, birth_date: birthDate || null, native_place: nativePlace || null, biography: biography || null, verification_status: status }
    try {
      if (person) await api.updatePerson(person.id, payload)
      else await api.createPerson(payload)
      await onSaved()
      onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '保存失败')
    }
  }

  const remove = async () => {
    if (!person || !window.confirm(`确定删除“${person.name}”及其关系吗？`)) return
    try {
      await api.deletePerson(person.id)
      await onSaved()
      onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '删除失败')
    }
  }

  return <div className="dialog-backdrop" role="presentation"><section className="editor-card" role="dialog" aria-modal="true" aria-labelledby="person-editor-title">
    <div className="panel-title"><div><span>人物档案</span><h2 id="person-editor-title">{person ? '编辑成员' : '新增成员'}</h2></div><button type="button" onClick={onClose}>关闭</button></div>
    <form className="editor-form" onSubmit={submit}>
      <label>姓名<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
      <label>性别<select value={gender} onChange={(event) => setGender(event.target.value as Gender)}><option value="unknown">未知</option><option value="male">男</option><option value="female">女</option></select></label>
      <label>出生信息<input value={birthDate} onChange={(event) => setBirthDate(event.target.value)} placeholder="如 1975 或 1975-06-12" /></label>
      <label>籍贯<input value={nativePlace} onChange={(event) => setNativePlace(event.target.value)} /></label>
      <label className="wide-field">简介<textarea value={biography} onChange={(event) => setBiography(event.target.value)} /></label>
      <label>核实状态<select value={status} onChange={(event) => setStatus(event.target.value as VerificationStatus)}><option value="unverified">待核实</option><option value="verified">已核实</option><option value="conflicting">存在冲突</option></select></label>
      {error && <p className="form-error wide-field" role="alert">{error}</p>}
      <div className="editor-actions wide-field">{person && <button type="button" className="danger-button" onClick={remove}>删除成员</button>}<button type="button" className="cancel-button" onClick={onClose}>取消</button><button className="confirm-button">保存人物</button></div>
    </form>
  </section></div>
}
