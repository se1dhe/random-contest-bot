"""
Скрипт для удаления всех конкурсов из базы данных
"""
import asyncio
import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete
from database.models import Contest, Prize, Participant, Sponsor
from database.db import get_database_url
from shared.config import config


async def delete_all_contests():
    """
    Удалить все конкурсы из базы данных
    
    Внимание: это удалит все конкурсы, призы, участников и спонсоров!
    """
    # Создаем подключение к БД
    database_url = get_database_url()
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Подсчитываем количество конкурсов перед удалением
            result = await db.execute(select(Contest))
            contests = result.scalars().all()
            contests_count = len(contests)
            
            if contests_count == 0:
                print("В базе данных нет конкурсов для удаления.")
                return
            
            print(f"Найдено конкурсов: {contests_count}")
            print("Внимание: будут удалены все конкурсы, призы, участники и спонсоры!")
            
            # Удаляем всех участников
            await db.execute(delete(Participant))
            print("✓ Удалены все участники")
            
            # Удаляем все призы
            await db.execute(delete(Prize))
            print("✓ Удалены все призы")
            
            # Удаляем всех спонсоров
            await db.execute(delete(Sponsor))
            print("✓ Удалены все спонсоры")
            
            # Удаляем все конкурсы
            await db.execute(delete(Contest))
            print("✓ Удалены все конкурсы")
            
            # Коммитим изменения
            await db.commit()
            
            print(f"\n✅ Успешно удалено {contests_count} конкурсов и связанные данные!")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Ошибка при удалении: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("=" * 50)
    print("Удаление всех конкурсов из базы данных")
    print("=" * 50)
    
    confirm = input("\nВы уверены, что хотите удалить ВСЕ конкурсы? (yes/no): ")
    
    if confirm.lower() != "yes":
        print("Операция отменена.")
        sys.exit(0)
    
    asyncio.run(delete_all_contests())
