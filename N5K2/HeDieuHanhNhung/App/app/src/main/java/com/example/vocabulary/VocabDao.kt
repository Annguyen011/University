package com.example.vocabulary

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface VocabDao {
    @Query("SELECT * FROM vocab")
    fun getAllVocab(): Flow<List<VocabEntity>>

    @Query("SELECT * FROM phrase")
    fun getAllPhrases(): Flow<List<PhraseEntity>>

    @Query("SELECT * FROM grammar")
    fun getAllGrammar(): Flow<List<GrammarEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertVocab(vocab: VocabEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPhrase(phrase: PhraseEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertGrammar(grammar: GrammarEntity)

    @Update
    suspend fun updateVocab(vocab: VocabEntity)

    @Delete
    suspend fun deleteVocab(vocab: VocabEntity)

    @Query("SELECT * FROM vocab WHERE word = :word LIMIT 1")
    suspend fun getVocabByWord(word: String): VocabEntity?
}
