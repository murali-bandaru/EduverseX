
// small helpers
function postJSON(url, data){
  return fetch(url, {
    method:'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data)
  }).then(r => r.json());
}

async function dailyCheckin(){
  const res = await postJSON('/daily_checkin', {});
  if(res.status === 'ok'){
    alert('Checked in! Points: '+res.points);
    location.reload();
  } else if(res.status === 'already'){
    alert('Already checked in today. Points: '+res.points);
  } else if(res.status === 'login_required'){
    alert('Please login to check-in.');
    window.location='/login';
  }
}
