export const S = {
  auth: null,
  me: null,
  users: [],
  items: [],
  month: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  selected: new Date().toISOString().slice(0, 10),
  weekStart: null,
  view: 'month'
};
