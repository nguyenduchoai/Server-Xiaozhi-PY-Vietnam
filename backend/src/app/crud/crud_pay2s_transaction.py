"""
Pay2s Transaction CRUD Operations
"""

from fastcrud import FastCRUD

from app.models.pay2s_transaction import Pay2sTransaction

CRUDPay2sTransaction = FastCRUD[Pay2sTransaction, None, None, None, None]
crud_pay2s_transaction = CRUDPay2sTransaction(Pay2sTransaction)
