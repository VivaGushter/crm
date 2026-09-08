import { $ } from './utils.js';
export function openModal(id) { $(id).classList.add('open'); document.body.style.overflow = 'hidden'; }
export function closeModal(id) { $(id).classList.remove('open'); document.body.style.overflow = ''; }
export function toggleDropdown() { $('dropdownMenu').classList.toggle('show'); }
export function closeDropdown() { $('dropdownMenu').classList.remove('show'); }
