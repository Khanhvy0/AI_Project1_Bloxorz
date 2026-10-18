# Maze Game Note
## About The Game
You are giving:  
- **A 1x1x2 rectangle**  
- **Your mission**: is to move the that rectangle to fall up right to the destination hole  


## Analyze

- **Rectangle State**: [Stand up, Lie down]
- **Moves** that the rectangle can do [Up, Down, Left, Right]  
- **Valid Move**: is a move that the rectangle still stay on the maze( not falls outside the maze), any attempts makes the rectangle fall outside the grid is an invalid move  
- **Input**: rectangle's start position, a grid of cell valid cell and void  
- **Output**: a sequence of moves from start to finish  

The rectangle changes it state when:  
- From `Stand up` to `Lie down`: any move when current state is `Stand up`   
- From `Lie down` to `Stand up`: any move on the long axis of the rectangle  

**Can we accomplish such taks using search method?**  
$\rightarrow$ Yes we can. Then how can we do it?  

**Problem**:
- What is the **model link** to bring from **maze $\rightarrow$ graph**  
- There are 3 state transition:  
    + `Stand up` $\rightarrow$ `Lie down`: Any move  
    + `Lie down` $\rightarrow$ `Stand up`: any move **paralell** with the long axis  
    + `Lie down` $\rigtharrow$ `Lie down`: Any move **perpendicular** with the long axis  

- Is the cost of any moves stand the same?  
- The rectangle has 2 states,how can we combine them to make a valid sequence?  
- How do we map **grid tiles $\rightarrow$ graph nodes** 
    + 2 subGraphs: one for `Stand up` state and one for `Lie down` state.  
    + 2 tiles create one node in graph `Lie down`  
    + 1 tiles create one node in graph `Stand up`
## UCS search

## A-start search