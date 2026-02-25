from fastapi import FastAPI,Depends,HTTPException,Request,UploadFile,File,Query,status,Response,Cookie
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import setting
from utility import hash_password,upload_file,success_response,error_response,PaginatedResponse,paginated_query,write_log_file,log_file_format
from typing import Annotated,List,Literal
from sqlalchemy.orm import Session,joinedload,selectinload
from sqlalchemy.exc import IntegrityError
from pydantic_models import UserOut,UserCreate,UserDbIn,NoteCreate,NoteOut,ApiResponse,QueryParams,NoteUpdate
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from dependencies import get_current_user,get_db,authenticate,token_generator,validate_tag,verify_token,required_permission
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
    print("Log is writing is started")
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
    print("Log already written")
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
@app.get("/health")
async def health_check():
    return {"status":"OK"}
@app.post("/register/",response_model=UserOut)
def register(user_data:UserCreate,db:Annotated[Session,Depends(get_db)],user_role:Literal["free_user","premium_user"]):
  db_data = UserDbIn(**user_data.model_dump(exclude={"password"}),hashed_password=hash_password(user_data.password))
  user = db_models.User(**db_data.model_dump())
  db.add(user) 
  if user_role == "premium_user":
    role = db.execute(select(db_models.Role).where(db_models.Role.name == user_role)).scalar_one()
  else:
    role = db.execute(select(db_models.Role).where(db_models.Role.name == user_role)).scalar_one()
  user.roles.append(role)
  
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
  if not user:
    raise credentials_exception
  perm = set()
  for role in user.roles:
    perm.update([p.name for p in role.permissions])
  print(f"User :::::--------> {user}")
  payload = {
    "sub":str(user.id),
    "type":"access",
    "roles":[r.name for r in user.roles],
    "perm":list(perm)
  }
  acces_token = token_generator(data=payload,secret_key=ACCESS_SECRET_KEY,token_expiry=timedelta(minutes=TOKEN_EXPIRY))
  refresh_token = token_generator(data={"sub":str(user.id)},secret_key=REFRESH_SECRET_KEY,token_expiry=timedelta(days=30))
  response = JSONResponse(
      status_code=200,
      content={
          "id":user.id,
          "username":user.username,
          "email":user.email,
          "full_name":user.full_name,
          "access_token":acces_token
          }
      )
  response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=False,
    max_age=7 * 24 * 60 * 60
  )
  return response


@app.post("/refresh/")
async def refresh(request:Request,db:Session = Depends(get_db)):
  refresh_token = request.cookies.get("refresh_token")
  if not refresh_token:
    raise HTTPException(401, "Missing refresh token")
  try:
    decoder = jwt.decode(refresh_token,REFRESH_SECRET_KEY,algorithms=[ALGOR])
    user_id = decoder.get("sub")
    if not user_id:
      raise HTTPException(401,"username doesn't exist!!!")
    user = db.execute(select(db_models.User).where(db_models.User.id == user_id)).scalar_one_or_none()
    print(f"User ::::::-----> {user}")
    if not user:
      raise HTTPException(401,"user doesn't exist!!!")
    perm = set()
    for role in user.roles:
      perm.update([p.name for p in role.permissions])
    payload = {
      "sub":str(user_id),
      "type":"access",
      "roles":[r.name for r in user.roles],
      "perm":list(perm)
    }
    access_token = token_generator(data=payload,secret_key=ACCESS_SECRET_KEY,token_expiry=timedelta(minutes=TOKEN_EXPIRY))
    return {"access_token":access_token,"token_type":"Bearer"}
  except InvalidTokenError:
    raise HTTPException(401,"Invalid Token!!!")
  
 
 
@app.get("/user-profile",response_model=ApiResponse[UserOut])
async def user_profile(current_user:db_models.User = Depends(required_permission(["users:read"])),db:Session = Depends(get_db)):
    user = db.execute(select(db_models.User).where(db_models.User.id == int(current_user["sub"]))).scalar_one_or_none()

    return success_response(
        message="user profile",
        data=UserOut.model_validate(user).model_dump(),
        status_code=status.HTTP_200_OK
    )
    
    
     
# **********************Note Endpoints ******************************* 
@app.post("/notes/")
async def create_note(
    current_user: Annotated[
        db_models.User,
        Depends(required_permission(["notes:create"]))
    ],
    files: Annotated[List[UploadFile], File(default_factory=list)],
    note: NoteCreate = Depends(NoteCreate.as_form),
    tag_names: List[str] = Depends(validate_tag),
    db: Session = Depends(get_db)
):
    existing_tags = []
    new_tags = []

    if tag_names:
        existing_tags = db.execute(
            select(db_models.Tag).where(db_models.Tag.name.in_(tag_names))
        ).scalars().all()

        existing_names = {tag.name for tag in existing_tags}
        new_tags = [
            db_models.Tag(name=name)
            for name in tag_names
            if name not in existing_names
        ]
        db.add_all(new_tags)

    note_for_db = db_models.Note(**note.model_dump(), user_id=int(current_user["sub"]))
    db.add(note_for_db)
    db.flush()

    note_for_db.tags.extend(existing_tags + new_tags)

    for f in files:
        f_path = upload_file(f)
        db.add(
            db_models.MediaFile(
                file_name=f.filename,
                file_path=f_path,
                content_type=f.content_type,
                note_id=note_for_db.id
            )
        )

    db.commit()
    return {"message": "note created successfully"}

  
@app.get("/notes/", response_model=ApiResponse[PaginatedResponse[NoteOut]])
async def get_notes(
    q: Annotated[QueryParams, Query()],
    current_user: Annotated[
        db_models.User,
        Depends(required_permission(["notes:read"]))
    ],
    db: Session = Depends(get_db)
):
    stmt = (
        select(db_models.Note)
        .options(
            selectinload(db_models.Note.tags),
            selectinload(db_models.Note.files)
        )
        .where(db_models.Note.user_id == int(current_user["sub"]))
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



@app.get("/notes/last-opened", response_model=ApiResponse[NoteOut])
async def get_last_opened_note(
    request: Request,
    current_user: Annotated[
        db_models.User,
        Depends(required_permission(["notes:read"]))
    ],
    db: Session = Depends(get_db)
):
    last_opened_note_id = request.cookies.get("last_note")
    if not last_opened_note_id:
        raise HTTPException(404, "No last opened note")

    note = db.execute(
        select(db_models.Note).where(
            db_models.Note.id == int(last_opened_note_id),
            db_models.Note.user_id == current_user.id
        )
    ).scalars().first()

    if not note:
        raise HTTPException(400, "Note doesn't exist")

    return success_response(
        message="Note fetched",
        status_code=200,
        data=note
    )


@app.get("/notes/{id}", response_model=ApiResponse[NoteOut])
async def get_note_by_id(
    id: int,
    response: Response,
    current_user: Annotated[
        db_models.User,
        Depends(required_permission(["notes:read"]))
    ],
    db: Session = Depends(get_db)
):
    note = db.execute(
        select(db_models.Note)
        .options(
            joinedload(db_models.Note.files),
            joinedload(db_models.Note.tags)
        )
        .where(
            db_models.Note.id == id,
            db_models.Note.user_id == current_user.id
        )
    ).scalars().first()

    if not note:
        raise HTTPException(404, "Note doesn't exist")

    response.set_cookie(
        key="last_note",
        value=id,
        httponly=True,
        max_age=60 * 60 * 24
    )

    return success_response(
        message="Note fetched successfully",
        status_code=200,
        data=note
    )

 
@app.put("/notes/{id}", response_model=ApiResponse[NoteOut])
async def update_note(
    id: int,
    note_content: NoteUpdate,
    current_user: Annotated[
        db_models.User,
        Depends(required_permission(["notes:update"]))
    ],
    db: Session = Depends(get_db),

):
    note_to_update = db.execute(
        select(db_models.Note)
        .options(
            joinedload(db_models.Note.files),
            joinedload(db_models.Note.tags)
        )
        .where(
            db_models.Note.id == id,
            db_models.Note.user_id == current_user.id
        )
    ).scalars().first()

    if not note_to_update:
        raise HTTPException(400, "Note doesn't exist")

    for key, value in note_content.model_dump(exclude_none=True).items():
        setattr(note_to_update, key, value)

    db.commit()
    return success_response(
        message="Note updated successfully",
        status_code=200,
        data=note_to_update
    )

  
@app.delete("/notes/{id}")
async def delete_note(
    id: int,
        current_user: Annotated[
        db_models.User,
        Depends(required_permission(["notes:delete"]))
    ],
    db: Session = Depends(get_db)

):
    note = db.execute(
        select(db_models.Note).where(
            db_models.Note.id == id,
            db_models.Note.user_id == current_user.id
        )
    ).scalars().first()

    if not note:
        raise HTTPException(400, "Note doesn't exist")

    db.delete(note)
    db.commit()
    return {"message": "Note successfully deleted"}



@app.post("/notes/{id}/tags", response_model=ApiResponse[NoteOut])
async def add_tags_to_note(
    id: int,
    current_user: Annotated[
        db_models.User,
        Depends(required_permission(["tags:create"]))
    ],
    tag_names: List[str] = Depends(validate_tag),
    db: Session = Depends(get_db)

):
    existing_tags = db.execute(
        select(db_models.Tag).where(db_models.Tag.name.in_(tag_names))
    ).scalars().all()

    existing_names = {t.name for t in existing_tags}
    new_tags = [
        db_models.Tag(name=name)
        for name in tag_names
        if name not in existing_names
    ]

    if not new_tags:
        raise HTTPException(422, "Tag already linked")

    db.add_all(new_tags)

    note = db.execute(
        select(db_models.Note)
        .options(
            joinedload(db_models.Note.tags),
            joinedload(db_models.Note.files)
        )
        .where(
            db_models.Note.id == id,
            db_models.Note.user_id == current_user.id
        )
    ).scalars().first()

    if not note:
        raise HTTPException(404, "Note doesn't exist")

    note.tags.extend(existing_tags + new_tags)
    db.commit()

    return success_response(
        message="Tags added successfully",
        status_code=200,
        data=note
    )


@app.post("/notes/{id}/files")
async def upload_file_to_note(
    id: int,
    files: Annotated[List[UploadFile], File(default_factory=list)],
        current_user: Annotated[
        db_models.User,
        Depends(required_permission(["files:upload"]))
    ],
    db: Session = Depends(get_db),

):
    note = db.execute(
        select(db_models.Note).where(
            db_models.Note.id == id,
            db_models.Note.user_id == current_user.id
        )
    ).scalars().first()

    if not note:
        raise HTTPException(400, "Note doesn't exist")

    for file in files:
        path = upload_file(file)
        db.add(
            db_models.MediaFile(
                file_name=file.filename,
                file_path=path,
                content_type=file.content_type,
                note_id=note.id
            )
        )

    db.commit()
    return success_response(
        message="File added successfully",
        status_code=201
    )


#to create seed permissions
@app.get("/create/permissions/")
async def generate_permission(
      current_user: Annotated[
        db_models.User,
        Depends(required_permission(["permissions:create"]))
    ],
    db: Session = Depends(get_db)
):
    seed_permissions(db)
    return {"message": "permissions created"}


#to link permissions with role
@app.get("/link-permission-role/")
async def link_permission_role(
    current_user: Annotated[
        db_models.User,
        Depends(required_permission(["roles:update"]))
    ],
    db: Session = Depends(get_db)
):
    assign_permission(db)
    return {"message": "roles linked with permissions"}
