from fastapi import FastAPI,Depends,HTTPException,Request,UploadFile,File,Query,status,Response,Cookie
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import setting
from utility import hash_password,upload_file,success_response,error_response,PaginatedResponse,paginated_query,write_log_file,log_file_format
from typing import Annotated,List
from sqlalchemy.orm import Session,joinedload,selectinload
from sqlalchemy.exc import IntegrityError
from pydantic_models import UserOut,UserCreate,UserDbIn,NoteCreate,NoteOut,ApiResponse,QueryParams,NoteUpdate
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from dependencies import get_current_user,get_db,authenticate,token_generator,validate_tag,verify_token
from sqlalchemy import select
from datetime import timedelta
from uuid import uuid4
from seed_permissions import seed_permissions,assign_permission
import jwt
import db_models
import time

# important variables

app = FastAPI()
ACCESS_SECRET_KEY = setting.ACCESS_SECRET_KEY
REFRESH_SECRET_KEY = setting.REFRESH_SECRET_KEY
ALGOR = setting.ALGORITHUM
TOKEN_EXPIRY = setting.TOKEN_EXPIRY_DATE
origin = [setting.ORIGIN]
# *******************default middleare ***********************
app.add_middleware(
  CORSMiddleware,
  allow_origins = origin,
  allow_credentials = True,
  allow_methods= ["*"],
  allow_headers=["*"]
)

# ****************** custom middleware ***********************
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def log_writer(request: Request, call_next):
    request_time = time.perf_counter()
    url = request.url.path
    method = request.method
    response = await call_next(request)
    user_id = getattr(request.state, "user_id", None)
    request_id = getattr(request.state, "request_id", None)
    response_time = (time.perf_counter() - request_time) * 1000
    response.headers['X-Response-Time'] = f"{response_time:.3f} ms"
    status_code = response.status_code

    data = log_file_format(
        method=method,
        url=url,
        user_id=user_id,
        status_code=status_code,
        response_time_ms=response_time,
        request_id=request_id
    )
    write_log_file(data=data)
    return response




# ************************ error response model **************************
@app.exception_handler(HTTPException)
async def http_excptions_handler(request:Request,exc:HTTPException):
  return error_response(status_code=exc.status_code,message=exc.detail,request_id=getattr(request.state, "request_id", None))
  
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request:Request,exc:RequestValidationError):
  field_errors = {}
  for err in exc.errors():
    field = err["loc"][-1]
    field_errors.setdefault(field,[]).append(err["msg"])
  return error_response(
              status_code=422,
              message="Validation error",
              errors=field_errors,
              request_id=getattr(request.state, "request_id", None)
            )
  
@app.exception_handler(Exception)
async def unhandled_exception_handler(request:Request,exc:Exception):
  return error_response(status_code=500,message="Something went wrong. Please try again later.",request_id=getattr(request.state, "request_id", None))
#endpoints  

# **********************Auth Endpoints******************************* 
@app.post("/register/",response_model=UserOut)
def register(user_data:UserCreate,db:Annotated[Session,Depends(get_db)]):
  db_data = UserDbIn(**user_data.model_dump(exclude={"password"}),hashed_password=hash_password(user_data.password))
  user = db_models.User(**db_data.model_dump())
  db.add(user)
    
  try:
    db.commit()
  except IntegrityError as e:
      db.rollback()
      if "email" in str(e.orig):
          raise HTTPException(409, "Email already registered")
      if "username" in str(e.orig):
          raise HTTPException(409, "Username already taken")
      raise HTTPException(400, "Invalid data")

  db.refresh(user)
  return UserOut.model_validate(user)

  
@app.post("/login/")
async def login(form:Annotated[OAuth2PasswordRequestForm,Depends()],db:Session = Depends(get_db)):
  username = form.username
  password = form.password
  credentials_exception = HTTPException(status_code=401,detail="Invalid username or password!!!",headers={"WWW-Authenticate":"Bearer"})
  user = authenticate(db,username,password)
  print(user.id)
  if not user:
    raise credentials_exception
  acces_token = token_generator(data={"sub":str(user.id),"type":"access"},secret_key=ACCESS_SECRET_KEY,token_expiry=timedelta(minutes=TOKEN_EXPIRY))
  refresh_token = token_generator(data={"sub":user.id,"type":"refresh"},secret_key=REFRESH_SECRET_KEY,token_expiry=timedelta(days=30))
  response = JSONResponse(status_code=200,content={"id":user.id,"username":user.username,"email":user.email,"full_name":user.full_name,"access_token":acces_token})
  response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=False,
    max_age=7 * 24 * 60 * 60
  )
  return response


@app.post("/refresh/")
async def refresh(request:Request):
  refresh_token = request.cookies.get("refresh_token")
  if not refresh_token:
    raise HTTPException(401, "Missing refresh token")
  try:
    decoder = jwt.decode(refresh_token,REFRESH_SECRET_KEY,algorithms=[ALGOR])
    user_id = decoder.get("sub")
    if not user_id:
      raise HTTPException(401,"username doesn't exist!!!")
    access_token = token_generator(data={"sub":user_id},secret_key=ACCESS_SECRET_KEY,token_expiry=timedelta(minutes=TOKEN_EXPIRY))
    return {"access_token":access_token,"token_type":"Bearer"}
  except InvalidTokenError:
    raise HTTPException(401,"Invalid Token!!!")
  
 
# **********************Note Endpoints ******************************* 
@app.post("/notes/")
async def create_note(
  user:Annotated[db_models.User,Depends(get_current_user)],
  files:Annotated[List[UploadFile],File(default_factory=list)],
  note:NoteCreate = Depends(NoteCreate.as_form), 
  tag_names:List[str]=Depends(validate_tag),
  db:Session = Depends(get_db)
  ):
  """pass tags as string separted by space
    eg: #tag1 #tag2 #tag3
  """
  existing_tags = []
  new_tags = []
  if tag_names:
    existing_tags = db.execute(select(db_models.Tag).where(db_models.Tag.name.in_(tag_names))).scalars().all()
    existing_names = {tag.name for tag in existing_tags}
    new_tags = [db_models.Tag(name=name) for name in tag_names if name not in existing_names]
    db.add_all(new_tags)
    
  note_for_db = db_models.Note(**note.model_dump(),user_id=user.id)
  db.add(note_for_db)
  db.flush()
  note_for_db.tags.extend(existing_tags + new_tags)
  

  for f in files:
    f_path = upload_file(f)
    files_for_db = db_models.MediaFile(file_name=f.filename,file_path=f_path,content_type=f.content_type,note_id=note_for_db.id)
    db.add(files_for_db)
  db.commit()
  
  return {"message":"note created successfully"}
  
@app.get(
    "/notes/",
    response_model=ApiResponse[PaginatedResponse[NoteOut]]
)
async def get_notes(
    q: Annotated[QueryParams, Query()],
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    stmt = (
        select(db_models.Note)
        .options(
            selectinload(db_models.Note.tags),
            selectinload(db_models.Note.files)
        )
        .where(db_models.Note.user_id == current_user.id)
        .order_by(db_models.Note.created_at.desc())
    )

    result = paginated_query(
        session=db,
        stmt=stmt,
        page=q.page,
        page_size=q.page_size
    )

    return success_response(
        message="Notes fetched successfully",
        data={
            "items": result["items"],
            "pagination": result["meta"]
        },
        status_code=status.HTTP_200_OK
    )


@app.get("/notes/last-opened",response_model=ApiResponse[NoteOut])
async def get_last_opened_note(request:Request,db:Session = Depends(get_db),current_user:db_models = Depends(get_current_user)):
  last_opened_note_id = request.cookies.get("last_note")
  if not last_opened_note_id:
    raise HTTPException(404, "No last opened note")
  note = db.execute(select(db_models.Note).where(db_models.Note.id == int(last_opened_note_id),db_models.Note.user_id == current_user.id)).scalars().first()
  if not note:
    raise HTTPException(400,"Note doesn't exist!!!")   
  return success_response(message="Note fetched",status_code=200,data=note)

@app.get("/notes/{id}",response_model=ApiResponse[NoteOut])
async def get_note_by_id(id:int,response:Response,db:Session = Depends(get_db),current_user:db_models.User = Depends(get_current_user)):
  
  note = db.execute(select(db_models.Note).options(joinedload(db_models.Note.files),joinedload(db_models.Note.tags)).where(db_models.Note.id == id,db_models.Note.user_id == current_user.id)).scalars().first()
  
  if not note:
    raise HTTPException(status_code=404,detail="Note doesn't exist.")
  response.set_cookie(key="last_note",value=id,secure=False,httponly=True,max_age=60 * 60 * 24)
  return success_response(message="Note fetched successfully!!!",status_code=status.HTTP_200_OK,data=note,meta=None)
 
@app.put("/notes/{id}",response_model=ApiResponse[NoteOut])
async def update_note(id:int,note_content:NoteUpdate,db:Session=Depends(get_db),current_user:db_models.User = Depends(get_current_user)):
  note_to_update = db.execute(select(db_models.Note).options(joinedload(db_models.Note.files),joinedload(db_models.Note.tags)).where(db_models.Note.id == id,db_models.Note.user_id == current_user.id)).scalars().first()
  if not note_to_update:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Note doesn't exist.")
  for key,value in note_content.model_dump(exclude_none=True).items():
    setattr(note_to_update,key,value)
  db.commit()
  return success_response(message="Note Updated Successfully!!!",status_code=status.HTTP_200_OK,data=note_to_update)
  
@app.delete("/notes/{id}")
async def delete_note(id:int,db:Session=Depends(get_db),current_user:db_models.User = Depends(get_current_user)):
  note_to_delete = db.execute(select(db_models.Note).options(joinedload(db_models.Note.files),joinedload(db_models.Note.tags)).where(db_models.Note.id == id,db_models.Note.user_id == current_user.id)).scalars().first()
  if not note_to_delete:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Note doesn't exist.")
  db.delete(note_to_delete)
  db.commit()

  return {"message":"Note successfully deleted!!!"}


@app.post("/notes/{id}/tags", response_model=ApiResponse[NoteOut])
async def add_tags_to_note(
    id: int,
    tag_names: List[str] = Depends(validate_tag),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    if not tag_names:
        raise HTTPException(
            status_code=400,
            detail="Please add tag names to attach with your note"
        )

    existing_tags = db.execute(select(db_models.Tag).where(db_models.Tag.name.in_(tag_names))).scalars().all()
    
    existing_tagnames = {tag.name for tag in existing_tags}
    new_tags = [
        db_models.Tag(name=name)
        for name in tag_names
        if name not in existing_tagnames
    ]
    if not new_tags:
      raise HTTPException(422,"Tag already linked")
    db.add_all(new_tags)

    note = db.execute(select(db_models.Note).options(joinedload(db_models.Note.files),joinedload(db_models.Note.tags)).where(db_models.Note.id == id,db_models.Note.user_id == current_user.id)).scalars().first()

    if not note:
        raise HTTPException(404, "Note doesn't exist")

    note.tags.extend(existing_tags + new_tags)
    db.commit()

    return ApiResponse(
        success=True,
        message="Tags added successfully to note",
        data=note
    )

@app.post("/notes/{id}/files")
async def upload_file_to_note(id:int,files:Annotated[List[UploadFile],File(default_factory=list)],db:Session = Depends(get_db),current_user:db_models.User = Depends(get_current_user)):
  note = db.execute(select(db_models.Note).options(joinedload(db_models.Note.files),joinedload(db_models.Note.tags)).where(db_models.Note.id == id,db_models.Note.user_id == current_user.id)).scalars().first()
  if not note:
    raise HTTPException(400,"Note doesn't exist!!!")
  for file in files:
    upload_get_path = upload_file(file)
    db.add(db_models.MediaFile(file_name=file.filename,file_path=upload_get_path,content_type=file.content_type,note_id=note.id))
  return success_response(message="File added successfully",status_code=201)




@app.post("/check/",dependencies=[Depends(verify_token)])
async def check(file:UploadFile):
  return {"file name":file.filename}


@app.get("/create/permissions/")
async def generate_permission(db:Session = Depends(get_db)):
  
  # create =  seed_permissions(db)
  # if create:
  #   return {"message":"permission created successfully."}
  assign_permission(db)
  return {"message":"role created  created"}